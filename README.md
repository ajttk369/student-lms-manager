# Student LMS Manager

Flask와 SQLite를 활용해 학생 정보를 등록, 조회, 수정, 삭제할 수 있는 관리자용 LMS 데이터 관리 페이지입니다.

## 제작 배경

실무에서는 HeidiSQL을 사용해 MySQL 기반 학생 데이터를 관리했습니다. 다만 포트폴리오 프로젝트로 그대로 구현할 경우, 보는 사람이 직접 실행하려면 MySQL 설치가 필요하고 DB 계정/비밀번호 설정까지 해야 하므로 테스트 환경 구성이 무거워지는 단점이 있습니다.

이 프로젝트는 채용 담당자나 리뷰어가 더 쉽게 실행하고 확인할 수 있도록 SQLite를 사용했습니다. 별도의 DB 서버 설치 없이 프로젝트를 실행하면 `data/lms.db` 파일이 자동으로 생성되어 CRUD 기능을 바로 테스트할 수 있습니다.

## 주요 기능

- 학생 등록, 수정, 삭제
- 이름, 연락처, 이메일, 메모 검색
- 수강 상태 및 과정별 필터링
- 전체, 수강중, 수료, 상담필요 통계 표시
- SQLite 기반 데이터 저장
- 반응형 관리자 UI

## 사용 기술

- Python
- Flask
- SQLite
- HTML
- CSS
- JavaScript
- Gunicorn

## 로컬 실행

```powershell
cd C:\Users\i5E-\Desktop\학생관리
pip install -r requirements.txt
python app.py
```

브라우저에서 아래 주소로 접속합니다.

```text
http://127.0.0.1:5000
```

`python` 명령이 동작하지 않으면 설치된 Python 실행 파일을 직접 지정합니다.

```powershell
C:\Users\i5E-\AppData\Local\Python\pythoncore-3.14-64\python.exe app.py
```

## Render 배포

1. 이 폴더를 GitHub 저장소에 업로드합니다.
2. Render에서 `New +` > `Web Service`를 선택합니다.
3. GitHub 저장소를 연결합니다.
4. 아래 설정을 입력합니다.

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --bind 0.0.0.0:$PORT
```

배포가 끝나면 Render에서 제공하는 URL을 포트폴리오의 `Live Demo` 버튼에 연결합니다.

## 포트폴리오 설명 예시

Student LMS Manager는 교육 운영자가 학생 데이터를 관리할 수 있도록 제작한 Flask 기반 관리자 페이지입니다. 학생 등록, 검색, 필터링, 수정, 삭제 기능을 구현했으며, 실무에서 HeidiSQL로 관리하던 학생 데이터 운영 흐름을 포트폴리오에서 쉽게 확인할 수 있도록 SQLite 기반 CRUD 프로젝트로 재구성했습니다.

## 데이터 저장

로컬 실행 시 데이터는 `data/lms.db`에 저장됩니다. 배포 환경에서는 서버 재시작 또는 재배포 시 SQLite 파일이 초기화될 수 있으므로, 장기 운영용으로 확장하려면 PostgreSQL, MySQL 같은 외부 DB 연결이 적합합니다.
