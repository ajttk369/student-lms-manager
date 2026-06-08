from __future__ import annotations

import csv
import io
import os
import sqlite3
from pathlib import Path

from flask import Flask, make_response, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "lms.db"

app = Flask(__name__)

STATUSES = ["수강중", "수료", "미수강", "상담필요"]
COURSES = ["웹 퍼블리싱", "프론트엔드", "Python 기초", "LMS 운영", "디자인"]
SAMPLE_STUDENTS = [
    ("김민준", "010-1234-2180", "minjun@example.com", "웹 퍼블리싱", "수강중", 68, "유종안", "과제 제출 일정 확인 필요"),
    ("이서연", "010-3210-4412", "seoyeon@example.com", "프론트엔드", "수료", 100, "유종안", "수료 처리 완료"),
    ("박지훈", "010-8821-0912", "jihoon@example.com", "Python 기초", "상담필요", 34, "유종안", "출석률 저하로 상담 예정"),
    ("최하린", "010-7421-6721", "harin@example.com", "LMS 운영", "미수강", 20, "유종안", "복귀 일정 확인 필요"),
    ("정도윤", "010-6671-5530", "doyun@example.com", "디자인", "수강중", 82, "유종안", "포트폴리오 피드백 진행"),
]
NOTICE_MESSAGES = {
    "created": "학생 정보가 등록되었습니다.",
    "updated": "학생 정보가 수정되었습니다.",
    "deleted": "학생 정보가 삭제되었습니다.",
    "reset": "데모 데이터가 초기 상태로 복구되었습니다.",
}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def clamp_progress(value: str | None) -> int:
    try:
        progress = int(value or 0)
    except ValueError:
        return 0
    return max(0, min(progress, 100))


def normalize_choice(value: str | None, options: list[str], default: str) -> str:
    value = (value or "").strip()
    return value if value in options else default


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
            insert_sample_students(conn)


def insert_sample_students(conn: sqlite3.Connection) -> None:
    conn.executemany(
        """
        INSERT INTO students (name, phone, email, course, status, progress, manager, memo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        SAMPLE_STUDENTS,
    )


def reset_demo_data() -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM students")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'students'")
        insert_sample_students(conn)


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
        totals = conn.execute("SELECT COUNT(*) AS total, COALESCE(ROUND(AVG(progress)), 0) AS average_progress FROM students").fetchone()
    by_status = {row["status"]: row["total"] for row in rows}
    return {
        "total": totals["total"],
        "active": by_status.get("수강중", 0),
        "completed": by_status.get("수료", 0),
        "needs_care": by_status.get("상담필요", 0),
        "average_progress": int(totals["average_progress"]),
    }


def get_course_summary() -> list[dict[str, int | str]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                course,
                COUNT(*) AS total,
                COALESCE(ROUND(AVG(progress)), 0) AS average_progress,
                SUM(CASE WHEN status = '상담필요' OR progress < 50 THEN 1 ELSE 0 END) AS risk_count
            FROM students
            GROUP BY course
            ORDER BY total DESC, course ASC
            """
        ).fetchall()
    return [
        {
            "course": row["course"],
            "total": row["total"],
            "average_progress": int(row["average_progress"]),
            "risk_count": row["risk_count"] or 0,
        }
        for row in rows
    ]


def get_priority_students() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT *
            FROM students
            WHERE status = '상담필요' OR progress < 50
            ORDER BY
                CASE WHEN status = '상담필요' THEN 0 ELSE 1 END,
                progress ASC,
                updated_at DESC
            LIMIT 4
            """
        ).fetchall()


def get_student(student_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()


def get_default_student_id() -> int | None:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM students ORDER BY id ASC LIMIT 1").fetchone()
    return row["id"] if row else None


def get_student_todos(student: sqlite3.Row) -> list[str]:
    todos = []
    if student["status"] == "상담필요":
        todos.append("담당자 상담 일정 확인")
    if student["progress"] < 50:
        todos.append("미완료 학습 진도 보강")
    if student["progress"] >= 80 and student["status"] == "수강중":
        todos.append("수료 기준 및 최종 과제 확인")
    if not todos:
        todos.append("현재 학습 진도 유지")
    return todos


@app.route("/")
def index():
    init_database()
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    course = request.args.get("course", "").strip()
    notice = NOTICE_MESSAGES.get(request.args.get("notice", ""))
    students = get_students(search=search, status=status, course=course)
    return render_template(
        "index.html",
        students=students,
        stats=get_stats(),
        course_summary=get_course_summary(),
        priority_students=get_priority_students(),
        statuses=STATUSES,
        courses=COURSES,
        filters={"search": search, "status": status, "course": course},
        notice=notice,
    )


@app.get("/portal")
def student_portal():
    init_database()
    students = get_students()
    selected_id = request.args.get("student_id", type=int) or get_default_student_id()
    selected_student = get_student(selected_id) if selected_id else None
    if selected_student is None and students:
        selected_student = students[0]
    return render_template(
        "portal.html",
        students=students,
        selected_student=selected_student,
        todos=get_student_todos(selected_student) if selected_student else [],
    )


@app.get("/students/export")
def export_students():
    init_database()
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    course = request.args.get("course", "").strip()
    students = get_students(search=search, status=status, course=course)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["이름", "연락처", "이메일", "과정", "상태", "진도", "담당자", "메모", "최근수정일"])
    for student in students:
        writer.writerow(
            [
                student["name"],
                student["phone"],
                student["email"] or "",
                student["course"],
                student["status"],
                student["progress"],
                student["manager"] or "",
                student["memo"] or "",
                student["updated_at"],
            ]
        )

    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=students.csv"
    return response


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
                normalize_choice(form.get("course"), COURSES, COURSES[0]),
                normalize_choice(form.get("status"), STATUSES, STATUSES[0]),
                clamp_progress(form.get("progress")),
                form.get("manager", "").strip(),
                form.get("memo", "").strip(),
            ),
        )
    return redirect(url_for("index", notice="created"))


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
                normalize_choice(form.get("course"), COURSES, COURSES[0]),
                normalize_choice(form.get("status"), STATUSES, STATUSES[0]),
                clamp_progress(form.get("progress")),
                form.get("manager", "").strip(),
                form.get("memo", "").strip(),
                student_id,
            ),
        )
    return redirect(url_for("index", notice="updated"))


@app.post("/students/<int:student_id>/delete")
def delete_student(student_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return redirect(url_for("index", notice="deleted"))


@app.post("/demo/reset")
def reset_demo():
    init_database()
    reset_demo_data()
    return redirect(url_for("index", notice="reset"))


if __name__ == "__main__":
    init_database()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
