import pandas as pd
from geopy.distance import geodesic
import requests
import time

# 출발좌표(심정지 좌표) 포함된 파일
start_df = pd.read_csv('emergency_sample.csv')

# 도착좌표(AED 좌표) 파일
dest_df = pd.read_csv('AED_sample.csv')

# 좌표 파싱 함수
def parse_coordinates(df):
    df['geometry_clean'] = df['geometry'].str.replace(r'POINT \(', '', regex=True).str.replace(r'\)', '', regex=True)
    df['경도'] = df['geometry_clean'].str.split().str[0].astype(float)
    df['위도'] = df['geometry_clean'].str.split().str[1].astype(float)
    return df

start_df = parse_coordinates(start_df)
dest_df = parse_coordinates(dest_df)

# [2] 최근접 도착지 찾기
def find_closest_destination(start_row):
    start_point = (start_row['위도'], start_row['경도'])
    min_dist = float('inf')
    closest_idx = None
    
    for dest_idx, dest_row in dest_df.iterrows():
        dest_point = (dest_row['위도'], dest_row['경도'])
        distance = geodesic(start_point, dest_point).meters
        if distance < min_dist:
            min_dist = distance
            closest_idx = dest_idx
    
    closest_dest = dest_df.loc[closest_idx]
    return pd.Series({
        '도착_위도': closest_dest['위도'],
        '도착_경도': closest_dest['경도']
    })

start_df[['도착_위도', '도착_경도']] = start_df.apply(find_closest_destination, axis=1)

# Tmap API 설정
TMAP_API_KEY = 'YEWVxfrK4j8xTNQZURJ4z1Te4JTZs26v45fgmfn7'

results = []

#  API 호출 및 결과 수집
for idx, row in start_df.iterrows():
    startX, startY = row['경도'], row['위도']
    endX, endY = row['도착_경도'], row['도착_위도']
    
    url = "https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1&callback=function"
    headers = {
        "appKey": TMAP_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "startX": str(startX),
        "startY": str(startY),
        "endX": str(endX),
        "endY": str(endY),
        "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO"
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            data = response.json()
            summary = data.get('features', [])[0]['properties']
            results.append({
                '출발_위도': startY,
                '출발_경도': startX,
                '도착_위도': endY,
                '도착_경도': endX,
                '거리(m)': summary.get('totalDistance'),
                '소요시간(초)': summary.get('totalTime'),
                'API_상태': '성공'
            })
        else:
            results.append({
                '출발_위도': startY,
                '출발_경도': startX,
                '도착_위도': endY,
                '도착_경도': endX,
                '거리(m)': None,
                '소요시간(초)': None,
                'API_상태': f'HTTP 에러({response.status_code})'
            })
    except Exception as e:
        results.append({
            '출발_위도': startY,
            '출발_경도': startX,
            '도착_위도': endY,
            '도착_경도': endX,
            '거리(m)': None,
            '소요시간(초)': None,
            'API_상태': f'예외 발생({str(e)})'
        })
    
    time.sleep(0.2)  # 과다 호출 방지

# 결과 저장
result_df = pd.DataFrame(results)
result_df.to_csv('Tmap_도보_길찾기_결과.csv', index=False)
print("결과 파일 저장 완료: Tmap_도보_길찾기_결과.csv")
