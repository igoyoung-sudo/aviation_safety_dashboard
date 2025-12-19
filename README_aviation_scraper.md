# Aviation Safety Network 터보프롭 항공기 데이터 수집기

Aviation Safety Network에서 터보프롭 항공기의 사고/사건 데이터를 자동으로 수집하는 Python 스크립트입니다.

## 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. Playwright 브라우저 설치:
```bash
playwright install chromium
```

## 사용 방법

### 기본 사용
모든 터보프롭 항공기 데이터 수집:
```bash
python aviation_safety_scraper.py
```

### 스크립트 수정하여 특정 항공기만 수집
`aviation_safety_scraper.py` 파일의 `main()` 함수에서 다음과 같이 수정:

```python
# ATR 72만 수집
await scraper.scrape_all({'_AT72': 'ATR 72 (all series)'})

# 여러 항공기 선택
selected_aircraft = {
    '_AT72': 'ATR 72 (all series)',
    'DH8D': 'Dash 8-400 (Q400)',
    'S340': 'Saab 340'
}
await scraper.scrape_all(selected_aircraft)
```

## 출력 파일

스크립트 실행 후 다음 파일이 생성됩니다:

1. **CSV 파일**: `aviation_safety_data_YYYYMMDD_HHMMSS.csv`
   - Excel, Google Sheets, Looker Studio 등에서 바로 사용 가능

2. **JSON 파일**: `aviation_safety_data_YYYYMMDD_HHMMSS.json`
   - 프로그래밍적으로 데이터를 처리할 때 사용

## 데이터 필드

각 레코드는 다음 필드를 포함합니다:

- `date`: 사고 날짜
- `type`: 항공기 상세 타입
- `registration`: 등록 번호
- `operator`: 운영 항공사
- `fatalities`: 사망자 수
- `location`: 사고 위치
- `damage`: 손상 정도 (w/o=전손, sub=상당, min=경미, non=없음)
- `aircraft_category`: 항공기 카테고리명
- `type_code`: 항공기 타입 코드

## 포함된 터보프롭 항공기

### ATR 시리즈
- ATR 72 (전 시리즈, 200, 210, 500, 600)
- ATR 42 (전 시리즈, 300, 400, 500, 600)

### De Havilland Canada
- Dash 8-100, 200, 300, 400 (Q400)
- DHC-6 Twin Otter
- DHC-7 Dash 7

### Saab
- Saab 340, Saab 2000

### Fokker
- Fokker 50, Fokker 60

### Embraer
- EMB-120 Brasilia

### Antonov (터보프롭)
- An-24, An-26, An-32, An-140

### 기타
- Let L-410
- Ilyushin Il-114
- Beech 1900
- Jetstream 31/41

## 대시보드 생성 가이드

### 방법 1: Google Looker Studio (추천)

1. **데이터 업로드**
   - Looker Studio (https://lookerstudio.google.com/) 접속
   - "만들기" → "데이터 소스"
   - "파일 업로드" 선택
   - 생성된 CSV 파일 업로드

2. **보고서 만들기**
   - "만들기" → "보고서"
   - 업로드한 데이터 소스 선택
   - 다음과 같은 시각화 추가:
     - **시계열 차트**: 연도별 사고 추이
     - **막대 차트**: 항공기 타입별 사고 건수
     - **파이 차트**: 손상 정도 분포
     - **지도**: 사고 발생 위치 (location 필드 사용)
     - **표**: 사망자가 발생한 주요 사고 목록
     - **스코어카드**: 총 사고 건수, 총 사망자 수

3. **필터 추가**
   - 항공기 카테고리별 필터
   - 날짜 범위 필터
   - 운영 항공사별 필터

### 방법 2: Google Sheets + 차트

1. CSV 파일을 Google Sheets에 업로드
2. "삽입" → "차트"를 통해 다양한 차트 생성
3. 피벗 테이블로 통계 분석

### 방법 3: Python으로 대시보드 생성

Plotly Dash나 Streamlit을 사용하여 인터랙티브 대시보드 생성:

```python
# 예시: Streamlit 사용
import streamlit as st
import pandas as pd
import plotly.express as px

df = pd.read_csv('aviation_safety_data_YYYYMMDD_HHMMSS.csv')

st.title('터보프롭 항공기 안전 데이터 대시보드')

# 차트 1: 항공기별 사고 건수
fig1 = px.bar(df['aircraft_category'].value_counts(),
              title='항공기 타입별 사고 건수')
st.plotly_chart(fig1)

# 차트 2: 연도별 추이
df['year'] = pd.to_datetime(df['date']).dt.year
fig2 = px.line(df.groupby('year').size(),
               title='연도별 사고 추이')
st.plotly_chart(fig2)
```

### 방법 4: Tableau Public

1. Tableau Public (무료) 다운로드
2. CSV 파일 연결
3. 드래그 앤 드롭으로 대시보드 생성
4. Tableau Public에 게시하여 공유

## 주의사항

- 웹 스크래핑이므로 Aviation Safety Network 서버에 부하를 주지 않도록 주의
- 스크립트는 요청 사이에 0.5초 대기 시간을 포함
- 데이터는 Aviation Safety Network의 저작권 정책을 준수하여 사용

## 문제 해결

### Playwright 설치 오류
```bash
# Playwright 재설치
pip uninstall playwright
pip install playwright
playwright install chromium
```

### 데이터 수집 실패
- 인터넷 연결 확인
- Aviation Safety Network 사이트 접속 가능 여부 확인
- 타임아웃 시간 늘리기 (스크립트에서 `timeout=30000` 값 증가)

## 라이선스

이 스크립트는 교육 및 연구 목적으로 제공됩니다.
수집된 데이터는 Aviation Safety Network의 저작권을 따릅니다.
