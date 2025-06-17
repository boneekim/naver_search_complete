import streamlit as st
import webbrowser
import urllib.parse
import threading
import time
import json
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook, load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
from datetime import datetime, timedelta
import io

# 페이지 설정
st.set_page_config(
    page_title="보니의 웹 크롤링 프로그램",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
def initialize_session_state():
    """세션 상태 변수 초기화"""
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'original_search_results' not in st.session_state:
        st.session_state.original_search_results = []
    if 'favorites' not in st.session_state:
        st.session_state.favorites = set()
    if 'search_history' not in st.session_state:
        st.session_state.search_history = load_search_history()
    if 'current_keyword' not in st.session_state:
        st.session_state.current_keyword = ""
    if 'exclude_keywords' not in st.session_state:
        st.session_state.exclude_keywords = []
    if 'show_favorites_only' not in st.session_state:
        st.session_state.show_favorites_only = False
    if 'searching' not in st.session_state:
        st.session_state.searching = False

def load_search_history():
    """검색 히스토리 로드"""
    history_file = "search_history.json"
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []

def save_search_history():
    """검색 히스토리 저장"""
    history_file = "search_history.json"
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.search_history[-20:], f, ensure_ascii=False, indent=2)
    except:
        pass

def add_to_history(keyword):
    """검색 히스토리에 키워드 추가"""
    if keyword and keyword.strip():
        keyword = keyword.strip()
        if keyword in st.session_state.search_history:
            st.session_state.search_history.remove(keyword)
        st.session_state.search_history.append(keyword)
        save_search_history()

def parse_date_for_sorting(date_str):
    """날짜 문자열을 정렬용 datetime 객체로 변환"""
    if not date_str or date_str == "날짜 정보 없음":
        return datetime.min
    
    current_time = datetime.now()
    
    # 상대적 시간 표현 처리
    if "분 전" in date_str:
        try:
            minutes = int(re.search(r'(\d+)분', date_str).group(1))
            return current_time - timedelta(minutes=minutes)
        except:
            pass
    elif "시간 전" in date_str:
        try:
            hours = int(re.search(r'(\d+)시간', date_str).group(1))
            return current_time - timedelta(hours=hours)
        except:
            pass
    elif "일 전" in date_str or "일전" in date_str:
        try:
            days = int(re.search(r'(\d+)일', date_str).group(1))
            return current_time - timedelta(days=days)
        except:
            pass
    elif "주 전" in date_str or "주전" in date_str:
        try:
            weeks = int(re.search(r'(\d+)주', date_str).group(1))
            return current_time - timedelta(weeks=weeks)
        except:
            pass
    elif "개월 전" in date_str or "달 전" in date_str:
        try:
            months = int(re.search(r'(\d+)개월|(\d+)달', date_str).group(1))
            return current_time - timedelta(days=months*30)
        except:
            pass
    elif "년 전" in date_str:
        try:
            years = int(re.search(r'(\d+)년', date_str).group(1))
            return current_time - timedelta(days=years*365)
        except:
            pass
    
    # 절대 날짜 형식 처리
    try:
        # 2024.01.15 형식
        if re.match(r'\d{4}\.\d{1,2}\.\d{1,2}', date_str):
            return datetime.strptime(date_str[:10], '%Y.%m.%d')
        # 01.15 형식 (현재 년도로 가정)
        elif re.match(r'\d{1,2}\.\d{1,2}', date_str):
            return datetime.strptime(f"{current_time.year}.{date_str}", '%Y.%m.%d')
    except:
        pass
    
    # 모든 파싱이 실패한 경우 현재 시간 반환
    return current_time

def is_within_one_month(date_str):
    """날짜가 1개월 이내인지 확인"""
    if not date_str or date_str == "날짜 정보 없음":
        return False
    
    try:
        parsed_date = parse_date_for_sorting(date_str)
        if parsed_date == datetime.min:
            return False
        
        current_time = datetime.now()
        one_month_ago = current_time - timedelta(days=30)
        
        return parsed_date >= one_month_ago
    except:
        return False

@st.cache_data(ttl=300)
def scrape_naver(encoded_keyword, search_type):
    """네이버 검색 (카페, 블로그)"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Streamlit Cloud에서는 chromium-driver를 사용
    try:
        # 로컬에서는 ChromeDriverManager 사용
        service = Service(ChromeDriverManager().install())
    except:
        # Streamlit Cloud에서는 시스템 chromedriver 사용
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    
    driver = None
    results = []
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        if search_type == 'cafe':
            url = f"https://search.naver.com/search.naver?where=article&query={encoded_keyword}&sm=tab_nmr&nso=so%3Ar%2Cp%3Aall"
        else:  # blog
            url = f"https://search.naver.com/search.naver?where=post&query={encoded_keyword}&sm=tab_nmr&nso=so%3Ar%2Cp%3Aall"
        
        driver.get(url)
        time.sleep(3)
        
        # 결과 요소들 찾기
        if search_type == 'cafe':
            elements = driver.find_elements(By.CSS_SELECTOR, ".bx, .detail_box, .total_wrap")
        else:
            elements = driver.find_elements(By.CSS_SELECTOR, ".bx, .detail_box, .total_wrap")
        
        count = 0
        for element in elements:
            if count >= 20:  # 최대 20개
                break
                
            try:
                # 제목 찾기
                title_elem = element.find_element(By.CSS_SELECTOR, "a.title_link, .title a, a.link_tit")
                title = title_elem.text.strip()
                link = title_elem.get_attribute('href')
                
                if not title or not link:
                    continue
                
                # 내용 추출
                content = extract_content(element)
                
                # 날짜 추출
                date = extract_date(element)
                
                # 1개월 이내 필터링
                if not is_within_one_month(date):
                    continue
                
                results.append({
                    'title': title,
                    'type': search_type,
                    'content': content,
                    'date': date,
                    'link': link
                })
                count += 1
                
            except:
                continue
                
    except Exception as e:
        st.error(f"{search_type} 검색 오류: {str(e)}")
    finally:
        if driver:
            driver.quit()
    
    return results

@st.cache_data(ttl=300)
def scrape_youtube(encoded_keyword):
    """유튜브 검색"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    
    # Streamlit Cloud에서는 chromium-driver를 사용
    try:
        # 로컬에서는 ChromeDriverManager 사용
        service = Service(ChromeDriverManager().install())
    except:
        # Streamlit Cloud에서는 시스템 chromedriver 사용
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    
    driver = None
    results = []
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        # 유튜브 검색 URL (최신순 정렬)
        url = f"https://www.youtube.com/results?search_query={encoded_keyword}&sp=CAI%253D"
        driver.get(url)
        time.sleep(5)
        
        # 스크롤하여 더 많은 결과 로드
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(3)
        
        # 비디오 요소들 찾기
        video_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")
        
        count = 0
        for element in video_elements:
            if count >= 20:  # 최대 20개
                break
                
            try:
                # 제목
                title_elem = element.find_element(By.CSS_SELECTOR, "#video-title")
                title = title_elem.text.strip()
                link = title_elem.get_attribute('href')
                
                if not title or not link:
                    continue
                
                # 전체 YouTube URL 생성
                if link.startswith('/watch'):
                    link = f"https://www.youtube.com{link}"
                
                # 업로드 날짜
                date_elem = element.find_element(By.CSS_SELECTOR, "#metadata-line span:nth-child(2)")
                date = date_elem.text.strip() if date_elem else "날짜 정보 없음"
                
                # 1개월 이내 필터링
                if not is_within_one_month(date):
                    continue
                
                # 채널명 추출
                try:
                    channel_elem = element.find_element(By.CSS_SELECTOR, "#channel-name a")
                    channel = channel_elem.text.strip()
                    content = f"채널: {channel}"
                except:
                    content = "유튜브 동영상"
                
                results.append({
                    'title': title,
                    'type': 'youtube',
                    'content': content,
                    'date': date,
                    'link': link
                })
                count += 1
                
            except:
                continue
                
    except Exception as e:
        st.error(f"YouTube 검색 오류: {str(e)}")
    finally:
        if driver:
            driver.quit()
    
    return results

def extract_content(element):
    """내용 요약 추출"""
    try:
        # 다양한 내용 선택자 시도
        content_selectors = [
            ".dsc_link", ".dsc", ".detail", ".desc", ".content",
            ".api_txt_lines", ".total_tit", ".sub_txt"
        ]
        
        for selector in content_selectors:
            try:
                content_elem = element.find_element(By.CSS_SELECTOR, selector)
                content = content_elem.text.strip()
                if content and len(content) > 10:
                    return content[:100] + "..." if len(content) > 100 else content
            except:
                continue
        
        # 대체 텍스트
        full_text = element.text.strip()
        if full_text:
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            for line in lines[1:]:  # 첫 번째 줄(제목) 제외
                if len(line) > 10 and not any(word in line for word in ['조회수', '댓글', '좋아요', '구독']):
                    return line[:100] + "..." if len(line) > 100 else line
        
        return "내용 요약 없음"
    except:
        return "내용 요약 없음"

def extract_date(element):
    """날짜 정보 추출"""
    try:
        # 다양한 날짜 선택자 시도
        date_selectors = [
            ".date", ".time", ".ago", ".sub_time", ".posting_date",
            ".created_time", ".txt_inline", ".sub_txt", ".txt_num"
        ]
        
        for selector in date_selectors:
            try:
                date_elem = element.find_element(By.CSS_SELECTOR, selector)
                date_text = date_elem.text.strip()
                if date_text and any(keyword in date_text for keyword in ['전', '시간', '분', '일', '월', '년', ':', '.']):
                    if any(char.isdigit() for char in date_text):
                        return date_text
            except:
                continue
        
        # 텍스트에서 직접 날짜 패턴 찾기
        full_text = element.text
        if full_text:
            # 상대적 시간 표현
            relative_patterns = [
                r'\d+분\s*전', r'\d+시간\s*전', r'\d+일\s*전',
                r'\d+개월\s*전', r'\d+년\s*전'
            ]
            for pattern in relative_patterns:
                match = re.search(pattern, full_text)
                if match:
                    return match.group()
            
            # 절대 날짜 표현
            absolute_patterns = [
                r'\d{4}\.\d{1,2}\.\d{1,2}',
                r'\d{1,2}\.\d{1,2}\.'
            ]
            for pattern in absolute_patterns:
                match = re.search(pattern, full_text)
                if match:
                    return match.group()
        
        return datetime.now().strftime("%Y.%m.%d")
    except:
        return datetime.now().strftime("%Y.%m.%d")

def apply_exclude_filters(results, exclude_keywords):
    """제외 키워드 필터 적용"""
    if not exclude_keywords:
        return results
    
    filtered_results = []
    for result in results:
        should_exclude = False
        
        for exclude_keyword in exclude_keywords:
            if exclude_keyword.lower() in result['title'].lower() or exclude_keyword.lower() in result['content'].lower():
                should_exclude = True
                break
        
        if not should_exclude:
            filtered_results.append(result)
    
    return filtered_results

def search_with_keywords(keywords, exclude_keywords=None):
    """키워드 검색 실행"""
    if not keywords or not any(k.strip() for k in keywords):
        st.error("검색할 키워드를 입력해주세요.")
        return
    
    # 유효한 키워드만 필터링
    valid_keywords = [k.strip() for k in keywords if k.strip()]
    if not valid_keywords:
        st.error("유효한 키워드를 입력해주세요.")
        return
    
    # AND 조건으로 키워드 결합
    keyword = " ".join(valid_keywords)
    st.session_state.current_keyword = keyword
    
    # 히스토리에 추가
    add_to_history(keyword)
    
    # 검색 상태 설정
    st.session_state.searching = True
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # URL 인코딩
        encoded_keyword = urllib.parse.quote(keyword)
        
        # 모든 검색 결과를 담을 리스트
        all_results = []
        
        # 1. 카페 검색
        status_text.text("카페 검색 중...")
        progress_bar.progress(20)
        cafe_results = scrape_naver(encoded_keyword, 'cafe')
        all_results.extend(cafe_results)
        st.success(f"카페 검색 완료: {len(cafe_results)}개 결과")
        
        # 2. 블로그 검색
        status_text.text("블로그 검색 중...")
        progress_bar.progress(50)
        blog_results = scrape_naver(encoded_keyword, 'blog')
        all_results.extend(blog_results)
        st.success(f"블로그 검색 완료: {len(blog_results)}개 결과")
        
        # 3. 유튜브 검색
        status_text.text("유튜브 검색 중...")
        progress_bar.progress(80)
        youtube_results = scrape_youtube(encoded_keyword)
        all_results.extend(youtube_results)
        st.success(f"유튜브 검색 완료: {len(youtube_results)}개 결과")
        
        # 결과 필터링 및 정렬
        status_text.text("결과 정리 중...")
        progress_bar.progress(90)
        
        # 제외 키워드 적용
        if exclude_keywords:
            all_results = apply_exclude_filters(all_results, exclude_keywords)
        
        # 날짜순 정렬 (최신순)
        all_results.sort(key=lambda x: parse_date_for_sorting(x['date']), reverse=True)
        
        # 세션 상태에 저장
        st.session_state.search_results = all_results
        st.session_state.original_search_results = all_results.copy()
        
        progress_bar.progress(100)
        status_text.text("검색 완료!")
        
        # 결과 요약
        total_count = len(all_results)
        cafe_count = len([r for r in all_results if r['type'] == 'cafe'])
        blog_count = len([r for r in all_results if r['type'] == 'blog'])
        youtube_count = len([r for r in all_results if r['type'] == 'youtube'])
        
        st.success(f"검색 완료! 총 {total_count}개 결과 (카페: {cafe_count}, 블로그: {blog_count}, 유튜브: {youtube_count})")
        
    except Exception as e:
        st.error(f"검색 중 오류가 발생했습니다: {str(e)}")
    finally:
        st.session_state.searching = False
        progress_bar.empty()
        status_text.empty()

def create_excel_download(results):
    """엑셀 파일 생성 및 다운로드 준비"""
    try:
        # DataFrame 생성
        data = []
        for result in results:
            data.append({
                '즐겨찾기': '⭐' if result['link'] in st.session_state.favorites else '☆',
                '제목': result['title'],
                '유형': result['type'],
                '내용요약': result['content'],
                '날짜': result['date'],
                '링크': result['link']
            })
        
        df = pd.DataFrame(data)
        
        # 엑셀 파일을 메모리에 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 시트명 설정
            current_date = datetime.now().strftime("%Y%m%d")
            sheet_name = f"{current_date},{st.session_state.current_keyword}"
            if len(sheet_name) > 31:
                sheet_name = sheet_name[:28] + "..."
            
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # 컬럼 너비 자동 조정
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        return output.getvalue()
    
    except Exception as e:
        st.error(f"엑셀 파일 생성 오류: {str(e)}")
        return None

def main():
    # 세션 상태 초기화
    initialize_session_state()
    
    # 메인 제목
    st.title("🕸️ 보니의 웹 크롤링 프로그램")
    st.markdown("네이버 카페, 블로그, 유튜브를 동시에 검색하고 결과를 관리하세요!")
    
    # 사이드바 - 검색 설정
    with st.sidebar:
        st.header("🔍 검색 설정")
        
        # 검색 키워드 입력
        st.subheader("검색 키워드 (AND 조건)")
        
        # 동적 키워드 입력
        if 'num_keywords' not in st.session_state:
            st.session_state.num_keywords = 1
        
        keywords = []
        for i in range(st.session_state.num_keywords):
            if i == 0:
                # 첫 번째 키워드는 히스토리 지원
                if st.session_state.search_history:
                    keyword = st.selectbox(
                        f"키워드 {i+1}:",
                        [""] + list(reversed(st.session_state.search_history)),
                        key=f"keyword_{i}"
                    )
                else:
                    keyword = st.text_input(f"키워드 {i+1}:", key=f"keyword_{i}")
            else:
                keyword = st.text_input(f"키워드 {i+1}:", key=f"keyword_{i}")
            keywords.append(keyword)
        
        # 키워드 추가/제거 버튼
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ 키워드 추가"):
                st.session_state.num_keywords += 1
                st.rerun()
        with col2:
            if st.button("➖ 키워드 제거") and st.session_state.num_keywords > 1:
                st.session_state.num_keywords -= 1
                st.rerun()
        
        # 제외 키워드
        st.subheader("제외 키워드")
        exclude_keywords_text = st.text_area(
            "제외할 키워드 (쉼표로 구분)",
            help="결과에서 제외할 키워드들을 쉼표로 구분하여 입력하세요"
        )
        exclude_keywords = [k.strip() for k in exclude_keywords_text.split(",") if k.strip()] if exclude_keywords_text else []
        
        # 검색 버튼
        search_clicked = st.button("🔍 검색 시작", type="primary", disabled=st.session_state.searching)
        
        # 히스토리 관리
        if st.session_state.search_history:
            st.subheader("검색 히스토리")
            if st.button("🗑️ 히스토리 삭제"):
                st.session_state.search_history = []
                save_search_history()
                st.success("히스토리가 삭제되었습니다.")
                st.rerun()
    
    # 검색 실행
    if search_clicked:
        search_with_keywords(keywords, exclude_keywords)
    
    # 메인 영역 - 검색 결과
    if st.session_state.search_results:
        st.header("📊 검색 결과")
        
        # 결과 필터링 옵션
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            show_favorites = st.checkbox("⭐ 즐겨찾기만 보기", value=st.session_state.show_favorites_only)
            st.session_state.show_favorites_only = show_favorites
        
        with col2:
            if st.button("🗑️ 즐겨찾기 초기화"):
                st.session_state.favorites = set()
                st.success("즐겨찾기가 초기화되었습니다.")
                st.rerun()
        
        with col3:
            # 엑셀 다운로드
            if st.session_state.search_results:
                excel_data = create_excel_download(st.session_state.search_results)
                if excel_data:
                    current_date = datetime.now().strftime("%Y%m%d")
                    filename = f"{current_date}-{st.session_state.current_keyword}.xlsx"
                    st.download_button(
                        label="📊 엑셀 다운로드",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        # 결과 표시
        display_results = st.session_state.search_results
        if show_favorites:
            display_results = [r for r in st.session_state.search_results if r['link'] in st.session_state.favorites]
        
        if not display_results:
            if show_favorites:
                st.info("즐겨찾기한 항목이 없습니다.")
            else:
                st.info("검색 결과가 없습니다.")
        else:
            # 결과 통계
            total_count = len(display_results)
            cafe_count = len([r for r in display_results if r['type'] == 'cafe'])
            blog_count = len([r for r in display_results if r['type'] == 'blog'])
            youtube_count = len([r for r in display_results if r['type'] == 'youtube'])
            favorite_count = len([r for r in display_results if r['link'] in st.session_state.favorites])
            
            st.info(f"📈 총 {total_count}개 결과 (카페: {cafe_count}, 블로그: {blog_count}, 유튜브: {youtube_count}, 즐겨찾기: {favorite_count})")
            
            # 결과 테이블 생성
            for idx, result in enumerate(display_results):
                with st.container():
                    col1, col2, col3, col4 = st.columns([0.5, 3, 1, 1])
                    
                    with col1:
                        # 즐겨찾기 버튼
                        is_favorite = result['link'] in st.session_state.favorites
                        if st.button("⭐" if is_favorite else "☆", key=f"fav_{idx}"):
                            if is_favorite:
                                st.session_state.favorites.remove(result['link'])
                            else:
                                st.session_state.favorites.add(result['link'])
                            st.rerun()
                    
                    with col2:
                        # 제목과 링크
                        st.markdown(f"**[{result['title']}]({result['link']})**")
                        st.caption(f"{result['content']}")
                    
                    with col3:
                        # 유형 표시
                        type_emoji = {"cafe": "☕", "blog": "📝", "youtube": "🎥"}
                        st.write(f"{type_emoji.get(result['type'], '📄')} {result['type']}")
                    
                    with col4:
                        # 날짜
                        st.write(result['date'])
                    
                    st.divider()
    
    # 파일 업로드
    st.header("📁 엑셀 파일 불러오기")
    uploaded_file = st.file_uploader(
        "검색 결과 엑셀 파일을 업로드하세요",
        type=['xlsx', 'xls'],
        help="이전에 저장한 검색 결과를 불러올 수 있습니다"
    )
    
    if uploaded_file is not None:
        try:
            # 엑셀 파일 읽기
            df = pd.read_excel(uploaded_file)
            
            # 컬럼 확인
            required_columns = ['제목', '링크']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"필수 컬럼이 없습니다: {', '.join(missing_columns)}")
            else:
                # 데이터 변환
                loaded_results = []
                favorites_from_file = set()
                
                for _, row in df.iterrows():
                    try:
                        title = str(row['제목']).strip()
                        link = str(row['링크']).strip()
                        
                        if not title or title == 'nan' or not link or link == 'nan':
                            continue
                        
                        result_type = str(row.get('유형', 'excel')).strip()
                        if result_type == 'nan':
                            result_type = 'excel'
                        
                        content = str(row.get('내용요약', '엑셀에서 불러온 데이터')).strip()
                        if content == 'nan':
                            content = '엑셀에서 불러온 데이터'
                        
                        date = str(row.get('날짜', '날짜 정보 없음')).strip()
                        if date == 'nan':
                            date = '날짜 정보 없음'
                        
                        # 즐겨찾기 정보
                        if '즐겨찾기' in df.columns:
                            favorite_value = str(row['즐겨찾기']).strip()
                            if favorite_value == '⭐':
                                favorites_from_file.add(link)
                        
                        loaded_results.append({
                            'title': title,
                            'type': result_type,
                            'content': content,
                            'date': date,
                            'link': link
                        })
                        
                    except:
                        continue
                
                if loaded_results:
                    # 데이터 처리 방식 선택
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("기존 결과에 추가"):
                            st.session_state.search_results.extend(loaded_results)
                            st.session_state.favorites.update(favorites_from_file)
                            st.session_state.original_search_results = st.session_state.search_results.copy()
                            st.success(f"{len(loaded_results)}개 데이터가 추가되었습니다!")
                            st.rerun()
                    
                    with col2:
                        if st.button("기존 결과 대체"):
                            st.session_state.search_results = loaded_results
                            st.session_state.favorites = favorites_from_file
                            st.session_state.original_search_results = loaded_results.copy()
                            st.session_state.current_keyword = f"엑셀파일-{uploaded_file.name}"
                            st.success(f"{len(loaded_results)}개 데이터로 대체되었습니다!")
                            st.rerun()
                else:
                    st.warning("유효한 데이터를 찾을 수 없습니다.")
                    
        except Exception as e:
            st.error(f"파일 읽기 오류: {str(e)}")
    
    # 하단 정보
    st.markdown("---")
    st.markdown("""
    ### 💡 사용법
    1. **키워드 검색**: 사이드바에서 키워드를 입력하고 검색하세요
    2. **AND 조건**: 여러 키워드를 입력하면 모든 키워드가 포함된 결과만 표시됩니다
    3. **제외 키워드**: 특정 키워드가 포함된 결과를 제외할 수 있습니다
    4. **즐겨찾기**: ⭐ 버튼을 클릭하여 중요한 결과를 표시하세요
    5. **엑셀 저장**: 검색 결과를 엑셀 파일로 다운로드할 수 있습니다
    6. **파일 불러오기**: 이전에 저장한 엑셀 파일을 업로드할 수 있습니다
    """)

if __name__ == "__main__":
    main() 