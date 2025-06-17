# 🕸️ 보니의 웹 크롤링 프로그램 (Streamlit 버전)

네이버 카페, 블로그, 유튜브를 동시에 검색하고 결과를 관리하는 웹 애플리케이션입니다.

## 🚀 배포 방법

### 1. Streamlit Cloud 배포

1. **GitHub 리포지토리 생성**
   - 다음 파일들을 GitHub 리포지토리에 업로드:
     - `naver_search_streamlit.py` (메인 앱 파일)
     - `requirements_streamlit.txt` (패키지 의존성)
     - `packages.txt` (시스템 패키지)

2. **Streamlit Cloud 연결**
   - [Streamlit Cloud](https://streamlit.io/cloud) 방문
   - GitHub 계정으로 로그인
   - "New app" 클릭
   - GitHub 리포지토리 연결
   - Main file path: `naver_search_streamlit.py`
   - Deploy 클릭

### 2. 로컬 실행

```bash
# 패키지 설치
pip install -r requirements_streamlit.txt

# 앱 실행
streamlit run naver_search_streamlit.py
```

## 📱 사용법

### 1. 키워드 검색
- 사이드바에서 검색할 키워드 입력
- 여러 키워드 추가 가능 (AND 조건)
- "검색 시작" 버튼 클릭

### 2. 제외 키워드
- 결과에서 제외할 키워드를 쉼표로 구분하여 입력
- 실시간으로 필터링 적용

### 3. 결과 관리
- ⭐ 버튼으로 즐겨찾기 추가/제거
- "즐겨찾기만 보기" 옵션으로 필터링
- 제목 클릭으로 원본 페이지 이동

### 4. 엑셀 다운로드
- "엑셀 다운로드" 버튼으로 결과 저장
- 즐겨찾기 정보도 함께 저장

### 5. 파일 업로드
- 이전에 저장한 엑셀 파일 업로드 가능
- "기존 결과에 추가" 또는 "기존 결과 대체" 선택

## 🔧 주요 기능

### 검색 기능
- **네이버 카페**: 최신순 정렬, 1개월 이내 글
- **네이버 블로그**: 최신순 정렬, 1개월 이내 글  
- **유튜브**: 최신순 정렬, 1개월 이내 영상
- **AND 조건**: 모든 키워드가 포함된 결과만 표시
- **제외 키워드**: 특정 키워드 포함 결과 제외

### 결과 관리
- **즐겨찾기**: 중요한 결과 별표 표시
- **실시간 필터링**: 제외 키워드 즉시 적용
- **날짜순 정렬**: 최신 결과부터 표시
- **내용 요약**: 각 결과의 요약 정보 표시

### 데이터 관리
- **엑셀 저장**: 검색 결과를 Excel 형식으로 다운로드
- **파일 불러오기**: 기존 Excel 파일 업로드
- **검색 히스토리**: 이전 검색 키워드 자동 저장

## ⚠️ 주의사항

### Streamlit Cloud 배포시
- Chrome/Chromium 브라우저가 자동으로 설치됩니다
- 첫 실행시 패키지 설치로 시간이 걸릴 수 있습니다
- 크롤링 과정에서 일시적으로 로딩 시간이 발생할 수 있습니다

### 검색 제한
- 각 사이트당 최대 20개 결과
- 1개월 이내 게시물만 검색
- 네이버 검색 정책에 따른 제한 가능

### 성능 최적화
- `@st.cache_data` 데코레이터로 결과 캐싱 (5분)
- 동일한 키워드 재검색시 캐시된 결과 사용

## 📁 파일 구조

```
project/
├── naver_search_streamlit.py      # 메인 Streamlit 앱
├── requirements_streamlit.txt      # Python 패키지 의존성
├── packages.txt                    # 시스템 패키지 (Chrome)
├── README_streamlit.md            # 사용법 설명서
└── search_history.json           # 검색 히스토리 (자동생성)
```

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **크롤링**: Selenium + ChromeDriver
- **데이터 처리**: Pandas, BeautifulSoup
- **파일 처리**: OpenPyXL
- **배포**: Streamlit Cloud

## 🔄 tkinter 버전과의 차이점

| 기능 | tkinter 버전 | Streamlit 버전 |
|------|-------------|----------------|
| 실행 환경 | 데스크톱 앱 | 웹 브라우저 |
| 배포 | 로컬 설치 필요 | 클라우드 배포 가능 |
| UI | 네이티브 GUI | 웹 인터페이스 |
| 파일 저장 | 로컬 폴더 | 브라우저 다운로드 |
| 파일 불러오기 | 파일 탐색기 | 드래그앤드롭 |
| 즐겨찾기 | 세션 유지 | 세션 기반 |

## 🆘 문제 해결

### 검색이 안 되는 경우
1. 인터넷 연결 확인
2. 키워드를 다르게 입력해보기
3. 페이지 새로고침 후 재시도

### 배포가 안 되는 경우
1. `requirements_streamlit.txt` 파일 확인
2. `packages.txt` 파일 포함 여부 확인
3. GitHub 리포지토리 public 설정 확인

### 엑셀 다운로드가 안 되는 경우
1. 브라우저 다운로드 설정 확인
2. 팝업 차단 해제
3. 다른 브라우저에서 시도 