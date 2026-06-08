from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "lms.db"

app = Flask(__name__)

STATUSES = ["수강중", "수료", "미수강", "상담필요"]
COURSES = ["웹 퍼블리싱", "프론트엔드", "Python 기초", "LMS 운영", "디자인"]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                course TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT '수강중',
                progress INTEGER NOT NULL DEFAULT 0 CHECK(progress BETWEEN 0 AND 100),
                manager TEXT,
                memo TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if count == 0:
            conn.executemany(
                """
                INSERT INTO students (name, phone, email, course, status, progress, manager, memo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    ("김민준", "010-1234-2180", "minjun@example.com", "웹 퍼블리싱", "수강중", 68, "유종안", "과제 제출 일정 확인 필요"),
                    ("이서연", "010-3210-4412", "seoyeon@example.com", "프론트엔드", "수료", 100, "유종안", "수료 처리 완료"),
                    ("박지훈", "010-8821-0912", "jihoon@example.com", "Python 기초", "상담필요", 34, "유종안", "출석률 저하로 상담 예정"),
                    ("최하린", "010-7421-6721", "harin@example.com", "LMS 운영", "미수강", 20, "유종안", "복귀 일정 확인 필요"),
                    ("정도윤", "010-6671-5530", "doyun@example.com", "디자인", "수강중", 82, "유종안", "포트폴리오 피드백 진행"),
                ],
            )


def get_students(search: str = "", status: str = "", course: str = "") -> list[sqlite3.Row]:
    where = []
    params: list[str] = []
    if search:
        where.append("(name LIKE ? OR phone LIKE ? OR email LIKE ? OR memo LIKE ?)")
        keyword = f"%{search}%"
        params.extend([keyword, keyword, keyword, keyword])
    if status:
        where.append("status = ?")
        params.append(status)
    if course:
        where.append("course = ?")
        params.append(course)

    query = "SELECT * FROM students"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY updated_at DESC, id DESC"

    with get_connection() as conn:
        return conn.execute(query, params).fetchall()


def get_stats() -> dict[str, int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS total FROM students GROUP BY status").fetchall()
        total = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    by_status = {row["status"]: row["total"] for row in rows}
    return {
        "total": total,
        "active": by_status.get("수강중", 0),
        "completed": by_status.get("수료", 0),
        "needs_care": by_status.get("상담필요", 0),
    }


@app.route("/")
def index():
    init_database()
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    course = request.args.get("course", "").strip()
    students = get_students(search=search, status=status, course=course)
    return render_template(
        "index.html",
        students=students,
        stats=get_stats(),
        statuses=STATUSES,
        courses=COURSES,
        filters={"search": search, "status": status, "course": course},
    )


@app.post("/students")
def create_student():
    form = request.form
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO students (name, phone, email, course, status, progress, manager, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                form.get("name", "").strip(),
                form.get("phone", "").strip(),
                form.get("email", "").strip(),
                form.get("course", "웹 퍼블리싱"),
                form.get("status", "수강중"),
                int(form.get("progress", 0) or 0),
                form.get("manager", "").strip(),
                form.get("memo", "").strip(),
            ),
        )
    return redirect(url_for("index"))


@app.post("/students/<int:student_id>/update")
def update_student(student_id: int):
    form = request.form
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE students
            SET name = ?, phone = ?, email = ?, course = ?, status = ?, progress = ?,
                manager = ?, memo = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                form.get("name", "").strip(),
                form.get("phone", "").strip(),
                form.get("email", "").strip(),
                form.get("course", "웹 퍼블리싱"),
                form.get("status", "수강중"),
                int(form.get("progress", 0) or 0),
                form.get("manager", "").strip(),
                form.get("memo", "").strip(),
                student_id,
            ),
        )
    return redirect(url_for("index"))


@app.post("/students/<int:student_id>/delete")
def delete_student(student_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_database()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
