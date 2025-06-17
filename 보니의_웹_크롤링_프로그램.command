#!/bin/bash

# 보니의 웹 크롤링 프로그램 실행 스크립트
echo "보니의 웹 크롤링 프로그램을 시작합니다..."
echo "프로그램 경로: /Users/gimboni/Desktop/image-preview-app"
echo ""

# 프로그램 디렉토리로 이동
cd "/Users/gimboni/Desktop/image-preview-app"

# Python 가상환경이 있다면 활성화 (선택사항)
# source venv/bin/activate

# 프로그램 실행
echo "프로그램을 실행 중입니다..."
python3 naver_search_complete.py

# 프로그램 종료 후 잠시 대기
echo ""
echo "프로그램이 종료되었습니다."
echo "5초 후 창이 닫힙니다..."
sleep 5 