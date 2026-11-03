# PRD: DemoPort — 개발자 프로필 웹사이트

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 (초안) |
| 작성일 | 2026-11-03 |
| 작성자 | 이종현 (leejonghyun.gs@gmail.com) |
| 상태 | Draft |

---

## 1. 개요

### 1.1 배경
Python, HTML5, WMS(창고관리시스템) 개발 경력을 한곳에 정리해 보여줄 수 있는 개인 프로필 웹사이트가 필요하다. 이력서만으로는 전달하기 어려운 프로젝트 경험, 기술 스택, 업무 도메인(물류/WMS) 이해도를 시각적으로 보여주는 것이 목적이다.

### 1.2 목표
- 방문자가 **30초 안에** "어떤 개발자인지(주력 분야, 강점)"를 파악할 수 있다.
- 주요 프로젝트(특히 WMS 관련)를 사례 중심으로 소개한다.
- 채용 담당자·협업 제안자가 **바로 연락**할 수 있는 경로를 제공한다.

### 1.3 대상 사용자
| 사용자 | 주요 니즈 |
|---|---|
| 채용 담당자 / 헤드헌터 | 경력 요약, 기술 스택, 연락처 |
| 개발 리드 / 기술 면접관 | 프로젝트 상세, 기술적 의사결정, 코드 샘플 |
| 프로젝트 의뢰자 (물류/유통사) | WMS 도메인 경험, 구축 사례 |

---

## 2. 프로필 정보

| 항목 | 내용 |
|---|---|
| 이름 | 이종현 |
| 이메일 | leejonghyun.gs@gmail.com |
| 주력 분야 | Python, HTML5, WMS 개발 |
| GitHub / 블로그 | _(추후 입력)_ |
| 한 줄 소개 | _(예: "현장 물류를 코드로 최적화하는 WMS 개발자")_ |

---

## 3. 기능 요구사항

### 3.1 페이지 구성 (싱글 페이지 + 섹션 앵커)

| # | 섹션 | 설명 | 우선순위 |
|---|---|---|---|
| 1 | **Hero** | 이름, 한 줄 소개, 주력 분야 태그(Python · HTML5 · WMS), CTA 버튼(연락하기 / 프로젝트 보기) | P0 |
| 2 | **About** | 자기소개, 경력 요약, 개발 철학 | P0 |
| 3 | **Skills** | 기술 스택을 카테고리별로 표시 | P0 |
| 4 | **Projects** | 프로젝트 카드 목록 + 상세 보기 | P0 |
| 5 | **Experience** | 경력 타임라인 (회사, 기간, 역할, 주요 성과) | P1 |
| 6 | **Contact** | 이메일 링크, (선택) 문의 폼 | P0 |
| 7 | **Footer** | 저작권, 소셜 링크 | P1 |

### 3.2 Skills 섹션 상세
| 카테고리 | 예시 항목 |
|---|---|
| Backend | Python, Flask / FastAPI / Django, REST API |
| Frontend | HTML5, CSS3, JavaScript |
| Domain | WMS (입고·출고·재고·로케이션 관리, 피킹/패킹, 바코드/RFID 연동) |
| Data / Infra | RDBMS(SQL), Git, Linux |

> 실제 사용 기술은 작성자 확인 후 확정한다.

### 3.3 Projects 섹션 상세
각 프로젝트 카드에 포함할 정보:
- 프로젝트명, 기간, 역할
- 문제(Problem) → 해결(Solution) → 성과(Result, 가능하면 수치)
- 사용 기술 태그
- 링크 (데모 / GitHub, 있을 경우)
- 태그 필터: `Python` / `HTML5` / `WMS` (P1)

### 3.4 Contact 섹션
- `mailto:leejonghyun.gs@gmail.com` 링크 (P0)
- 이메일 주소 복사 버튼 (P1)
- 문의 폼 — 정적 호스팅 시 외부 폼 서비스 연동 검토 (P2)

### 3.5 공통 기능
- 상단 고정 내비게이션 + 섹션 스크롤 이동 (P0)
- 다크 / 라이트 모드 전환 (P1)
- 한국어 기본, 영어 전환 (P2)

---

## 4. 비기능 요구사항

| 항목 | 요구사항 |
|---|---|
| 반응형 | 모바일(360px) ~ 데스크톱(1440px) 대응 |
| 성능 | Lighthouse Performance 90점 이상, 첫 화면 로딩 2초 이내 |
| 접근성 | 시맨틱 HTML5 태그 사용, 이미지 alt, 키보드 탐색 가능, 명도 대비 WCAG AA |
| SEO | title/description 메타, Open Graph 태그, sitemap |
| 브라우저 | 최신 Chrome, Edge, Safari, Firefox |
| 유지보수 | 프로젝트·경력 데이터를 별도 데이터 파일(JSON)로 분리해 HTML 수정 없이 갱신 가능 |

---

## 5. 기술 스택 (제안)

| 영역 | 선택 | 이유 |
|---|---|---|
| 마크업 | HTML5 (시맨틱 태그) | 주력 분야를 직접 보여주는 결과물 |
| 스타일 | CSS3 (Flexbox/Grid, CSS 변수) | 프레임워크 없이 가볍게 유지 |
| 스크립트 | Vanilla JavaScript | 섹션 이동, 테마 전환, 데이터 렌더링 |
| 데이터 | `data/*.json` | 프로젝트·경력 정보 분리 관리 |
| 빌드/도구 (선택) | Python 스크립트 | JSON → HTML 정적 생성, 로컬 서버(`python -m http.server`) |
| 배포 | GitHub Pages 또는 Netlify | 무료, 정적 사이트에 적합 |

---

## 6. 폴더 구조 (제안)

```
DemoPort/
├── prd.md
├── index.html
├── css/
│   └── style.css
├── js/
│   └── main.js
├── data/
│   ├── profile.json
│   ├── skills.json
│   └── projects.json
└── assets/
    └── images/
```

---

## 7. 마일스톤

| 단계 | 내용 | 산출물 |
|---|---|---|
| M1 | PRD 확정 | prd.md |
| M2 | 와이어프레임 및 디자인 톤 결정 | 레이아웃 시안 |
| M3 | 기본 골격 구현 (Hero, About, Skills, Contact) | index.html, style.css |
| M4 | Projects / Experience 구현 + JSON 데이터 연동 | main.js, data/*.json |
| M5 | 반응형·접근성·SEO 점검 | Lighthouse 리포트 |
| M6 | 배포 | 공개 URL |

---

## 8. 성공 지표
- Lighthouse 성능·접근성·SEO 각 90점 이상
- 모바일/데스크톱 레이아웃 깨짐 없음
- 사이트를 통한 이메일 문의 발생

---

## 9. 미결 사항 (작성자 확인 필요)
- [ ] 한 줄 소개 문구
- [ ] 총 경력 연차 및 회사 이력
- [ ] 소개할 프로젝트 목록 (WMS 프로젝트 우선, 3~5개)
- [ ] 실제 사용 Python 프레임워크 / DB 종류
- [ ] GitHub, 블로그, LinkedIn 등 외부 링크
- [ ] 프로필 사진 사용 여부
- [ ] 배포 도메인 (GitHub Pages 기본 도메인 vs 개인 도메인)
