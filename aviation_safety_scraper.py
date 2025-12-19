#!/usr/bin/env python3
"""
Aviation Safety Network 터보프롭 항공기 사고 데이터 수집 스크립트
ATR72 및 기타 터보프롭 항공기의 사고/사건 데이터를 수집합니다.
"""

import asyncio
import csv
import json
from datetime import datetime
from playwright.async_api import async_playwright
import pandas as pd

# 주요 터보프롭 항공기 목록 (type code)
TURBOPROP_AIRCRAFT = {
    # ATR 시리즈
    '_AT72': 'ATR 72 (all series)',
    'AT72': 'ATR 72-200',
    'AT73': 'ATR 72-210',
    'AT75': 'ATR 72-500',
    'AT76': 'ATR 72-600',
    '_AT42': 'ATR 42 (all series)',
    'AT43': 'ATR 42-300',
    'AT44': 'ATR 42-400',
    'AT45': 'ATR 42-500',
    'AT46': 'ATR 42-600',

    # De Havilland Canada (Dash 8 / DHC)
    'DH8A': 'Dash 8-100',
    'DH8B': 'Dash 8-200',
    'DH8C': 'Dash 8-300',
    'DH8D': 'Dash 8-400 (Q400)',
    'DHC6': 'DHC-6 Twin Otter',
    'DHC7': 'DHC-7 Dash 7',

    # Saab
    'S340': 'Saab 340',
    'S2000': 'Saab 2000',

    # Fokker
    'F50': 'Fokker 50',
    'F60': 'Fokker 60',

    # Embraer
    'E120': 'EMB-120 Brasilia',

    # Antonov (터보프롭만)
    'AN24': 'Antonov An-24',
    'AN26': 'Antonov An-26',
    'AN32': 'Antonov An-32',
    'A140': 'Antonov An-140',

    # 기타 주요 터보프롭
    'L410': 'Let L-410',
    'IL114': 'Ilyushin Il-114',
    'B190': 'Beech 1900',
    'J31': 'Jetstream 31',
    'J41': 'Jetstream 41',
}


class AviationSafetyScraper:
    """Aviation Safety Network 데이터 수집기"""

    def __init__(self):
        self.base_url = "https://aviation-safety.net/asndb/type/"
        self.all_data = []

    async def scrape_aircraft_type(self, page, type_code, aircraft_name):
        """특정 항공기 타입의 데이터 수집"""
        url = f"{self.base_url}{type_code}"
        print(f"수집 중: {aircraft_name} ({url})")

        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(1)  # 페이지 로딩 대기

            # JavaScript로 테이블 데이터 추출
            data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    if (tables.length < 2) return [];

                    const dataTable = tables[1];
                    const rows = dataTable.querySelectorAll('tr');
                    const result = [];

                    // 헤더 제외하고 데이터 수집
                    for (let i = 1; i < rows.length; i++) {
                        const cells = Array.from(rows[i].querySelectorAll('td'));
                        if (cells.length > 0) {
                            const rowData = {
                                date: cells[0]?.textContent.trim() || '',
                                type: cells[1]?.textContent.trim() || '',
                                registration: cells[2]?.textContent.trim() || '',
                                operator: cells[3]?.textContent.trim() || '',
                                fatalities: cells[4]?.textContent.trim() || '',
                                location: cells[5]?.textContent.trim() || '',
                                damage: cells[7]?.textContent.trim() || ''
                            };
                            result.push(rowData);
                        }
                    }

                    return result;
                }
            """)

            # 항공기 정보 추가
            for record in data:
                record['aircraft_category'] = aircraft_name
                record['type_code'] = type_code
                self.all_data.append(record)

            print(f"  → {len(data)}개 레코드 수집 완료")
            return data

        except Exception as e:
            print(f"  ✗ 오류 발생: {str(e)}")
            return []

    async def scrape_all(self, aircraft_types=None):
        """모든 항공기 데이터 수집"""
        if aircraft_types is None:
            aircraft_types = TURBOPROP_AIRCRAFT

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            total = len(aircraft_types)
            for idx, (type_code, aircraft_name) in enumerate(aircraft_types.items(), 1):
                print(f"\n[{idx}/{total}]", end=" ")
                await self.scrape_aircraft_type(page, type_code, aircraft_name)
                await asyncio.sleep(0.5)  # 서버 부하 방지

            await browser.close()

        print(f"\n\n총 {len(self.all_data)}개의 레코드를 수집했습니다.")
        return self.all_data

    def save_to_csv(self, filename='aviation_safety_data.csv'):
        """CSV 파일로 저장"""
        if not self.all_data:
            print("저장할 데이터가 없습니다.")
            return

        df = pd.DataFrame(self.all_data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"CSV 파일 저장 완료: {filename}")

    def save_to_json(self, filename='aviation_safety_data.json'):
        """JSON 파일로 저장"""
        if not self.all_data:
            print("저장할 데이터가 없습니다.")
            return

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_data, f, ensure_ascii=False, indent=2)
        print(f"JSON 파일 저장 완료: {filename}")

    def get_statistics(self):
        """수집된 데이터의 통계 출력"""
        if not self.all_data:
            print("데이터가 없습니다.")
            return

        df = pd.DataFrame(self.all_data)

        print("\n" + "="*60)
        print("데이터 통계")
        print("="*60)
        print(f"총 레코드 수: {len(df)}")
        print(f"\n항공기별 사고 건수:")
        print(df['aircraft_category'].value_counts())

        # 사망자 수 통계
        df['fatalities_num'] = pd.to_numeric(df['fatalities'], errors='coerce')
        print(f"\n총 사망자 수: {df['fatalities_num'].sum():.0f}명")
        print(f"평균 사망자 수: {df['fatalities_num'].mean():.2f}명")

        # 손상 정도별 통계
        print(f"\n손상 정도별 분포:")
        print(df['damage'].value_counts())


async def main():
    """메인 실행 함수"""
    print("Aviation Safety Network 터보프롭 항공기 데이터 수집 시작")
    print("="*60)

    scraper = AviationSafetyScraper()

    # 데이터 수집 (특정 항공기만 수집하려면 딕셔너리를 전달)
    # 예: await scraper.scrape_all({'_AT72': 'ATR 72 (all series)'})
    await scraper.scrape_all()

    # 통계 출력
    scraper.get_statistics()

    # 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    scraper.save_to_csv(f'aviation_safety_data_{timestamp}.csv')
    scraper.save_to_json(f'aviation_safety_data_{timestamp}.json')

    print("\n데이터 수집 완료!")


if __name__ == "__main__":
    asyncio.run(main())
