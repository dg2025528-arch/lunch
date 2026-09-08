import requests
from datetime import datetime, timedelta
import calendar

class NeisMealAPI:
    BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def get_meal_by_date(self, edu_code, school_code, date):
        """특정 날짜 급식 조회"""
        params = {
            "KEY": self.api_key,
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": edu_code,
            "SD_SCHUL_CODE": school_code,
            "MLSV_YMD": date
        }
        response = requests.get(self.BASE_URL, params=params)
        return self._parse_response(response.json())
    
    def get_meal_by_month(self, edu_code, school_code, year, month):
        """월간 급식 조회"""
        start = f"{year}{month:02d}01"
        last_day = calendar.monthrange(year, month)[1]
        end = f"{year}{month:02d}{last_day}"
        
        params = {
            "KEY": self.api_key,
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": edu_code,
            "SD_SCHUL_CODE": school_code,
            "MLSV_FROM_YMD": start,
            "MLSV_TO_YMD": end
        }
        response = requests.get(self.BASE_URL, params=params)
        return self._parse_multiple(response.json())
    
    def get_meal_by_week(self, edu_code, school_code, start_date):
        """주간 급식 조회 (start_date부터 7일)"""
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = start_dt + timedelta(days=6)
        end_date = end_dt.strftime("%Y%m%d")
        
        params = {
            "KEY": self.api_key,
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": edu_code,
            "SD_SCHUL_CODE": school_code,
            "MLSV_FROM_YMD": start_date,
            "MLSV_TO_YMD": end_date
        }
        response = requests.get(self.BASE_URL, params=params)
        return self._parse_multiple(response.json())
    
    def _parse_response(self, data):
        try:
            meal_info = data["mealServiceDietInfo"][1]["row"][0]
            return self._format_meal(meal_info)
        except (KeyError, IndexError):
            return None
    
    def _parse_multiple(self, data):
        try:
            rows = data["mealServiceDietInfo"][1]["row"]
            return [self._format_meal(r) for r in rows]
        except (KeyError, IndexError):
            return []
    
    def _format_meal(self, meal_info):
        menu_raw = meal_info["DDISH_NM"].replace("<br/>", "\n")
        # 메뉴에서 알레르기 표시 숫자 제거 (예: "제육볶음(5.6.13)" -> "제육볶음")
        import re
        menu_clean = re.sub(r'\([\d.]+\)', '', menu_raw).strip()
        
        nutrition_raw = meal_info.get("NTR_INFO", "")
        nutrition_dict = self._parse_nutrition(nutrition_raw)
        
        return {
            "date": meal_info["MLSV_YMD"],
            "menu_raw": menu_raw,
            "menu": menu_clean,
            "menu_items": [m.strip() for m in menu_clean.split("\n") if m.strip()],
            "calorie": meal_info.get("CAL_INFO", "정보없음"),
            "nutrition": nutrition_dict
        }
    
    def _parse_nutrition(self, nutrition_str):
        """영양정보 문자열 파싱 -> dict"""
        result = {}
        if not nutrition_str:
            return result
        items = nutrition_str.replace("<br/>", "\n").split("\n")
        for item in items:
            if ":" in item:
                key, val = item.split(":", 1)
                # 숫자만 추출
                import re
                num_match = re.search(r'[\d.]+', val)
                if num_match:
                    result[key.strip()] = float(num_match.group())
        return result


class SchoolSearch:
    SEARCH_URL = "https://open.neis.go.kr/hub/schoolInfo"
    
    def __init__(self, api_key):
        self.api_key = api_key
    
    def search_school(self, school_name):
        params = {
            "KEY": self.api_key,
            "Type": "json",
            "SCHUL_NM": school_name
        }
        response = requests.get(self.SEARCH_URL, params=params)
        return self._parse_school_data(response.json())
    
    def _parse_school_data(self, data):
        try:
            schools = data["schoolInfo"][1]["row"]
            return [
                {
                    "name": s["SCHUL_NM"],
                    "edu_code": s["ATPT_OFCDC_SC_CODE"],
                    "school_code": s["SD_SCHUL_CODE"],
                    "address": s.get("ORG_RDNMA", "")
                }
                for s in schools
            ]
        except (KeyError, IndexError):
            return []
