# AI 정부지원금 & 세액공제 추천 서비스

기업 정보를 입력하면 세액공제 예상액, 맞는 정부지원사업, 1페이지 리포트를 보여 주는 시연용 프로토타입입니다. (마감: 2026-12-14, 제출 방식: **배포 URL**)

## 개발·배포 방식

- 코드 작성, 테스트, 화면 구동은 Claude Code(클라우드 작업 환경)에서 진행합니다. **내 PC에 Python을 설치하지 않아도 됩니다.**
- 발표는 배포 URL(Streamlit Community Cloud 등)로 합니다. 배포용 GitHub 저장소는 5주차에 만듭니다.
- API 키는 코드나 채팅에 넣지 않고, 배포 서비스의 비밀 설정(secrets) 또는 `.env`에만 넣습니다.

## (선택) 내 PC에서 직접 실행하고 싶다면 — Windows 기준

1. Python 3.11 이상 설치 (설치할 때 "Add Python to PATH"를 체크)
2. 이 폴더에서 터미널(PowerShell)을 열고 순서대로 입력

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

3. 브라우저에 화면이 열리면 성공입니다. (안 열리면 터미널에 나온 `http://localhost:8501` 주소를 직접 열기)

## Claude Code로 이어서 작업하기

- 이 폴더를 Claude Code로 열면 `CLAUDE.md`가 자동으로 읽혀서 프로젝트 규칙과 현재 상황을 바로 이해합니다.
- `/status`: 오늘 기준 진행 상황과 이번 주 할 일을 요약합니다.
- `/explain`: 방금 바뀐 내용을 쉬운 말로 설명합니다.

## 문서

`CLAUDE.md`의 "문서 지도"를 보세요.
