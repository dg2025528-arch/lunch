# 고기/육류 관련 키워드 (필요시 계속 추가 가능)
MEAT_KEYWORDS = [
    "고기", "돈육", "돼지", "소고기", "쇠고기", "닭", "치킨", "육류",
    "불고기", "제육", "삼겹살", "갈비", "탕수육", "돈까스", "돈가스",
    "베이컨", "햄", "소시지", "미트볼", "육개장", "설렁탕", "곰탕",
    "삼계탕", "닭갈비", "닭볶음탕", "오리", "육회", "장조림",
    "떡갈비", "완자", "너비아니", "훈제", "스테이크", "가츠",
    "육전", "편육", "수육", "족발", "보쌈", "잡채"  # 잡채는 고기 들어가는 경우多
]

# 생선/해산물 (페스코 베지테리언 판별용, 선택적)
SEAFOOD_KEYWORDS = [
    "생선", "고등어", "갈치", "명태", "동태", "오징어", "새우",
    "조개", "굴", "멸치", "어묵", "게맛살", "참치", "연어"
]


class VeganAnalyzer:
    def __init__(self, meat_keywords=None, seafood_keywords=None):
        self.meat_keywords = meat_keywords or MEAT_KEYWORDS
        self.seafood_keywords = seafood_keywords or SEAFOOD_KEYWORDS
    
    def contains_meat(self, menu_item):
        return any(kw in menu_item for kw in self.meat_keywords)
    
    def contains_seafood(self, menu_item):
        return any(kw in menu_item for kw in self.seafood_keywords)
    
    def analyze_meal(self, meal):
        """단일 급식(하루)에 대한 분석"""
        items = meal.get("menu_items", [])
        meat_items = [i for i in items if self.contains_meat(i)]
        seafood_items = [i for i in items if self.contains_seafood(i)]
        
        return {
            "date": meal["date"],
            "total_items": len(items),
            "meat_items": meat_items,
            "meat_count": len(meat_items),
            "seafood_items": seafood_items,
            "seafood_count": len(seafood_items),
            "is_vegan_friendly": len(meat_items) == 0 and len(seafood_items) == 0
        }
    
    def analyze_period(self, meals):
        """여러 날짜(주간/월간) 급식 분석 -> 통계"""
        results = [self.analyze_meal(m) for m in meals]
        total_days = len(results)
        if total_days == 0:
            return None
        
        meat_days = sum(1 for r in results if r["meat_count"] > 0)
        vegan_days = sum(1 for r in results if r["is_vegan_friendly"])
        
        return {
            "total_days": total_days,
            "meat_days": meat_days,
            "meat_ratio": round(meat_days / total_days * 100, 1),
            "vegan_friendly_days": vegan_days,
            "vegan_ratio": round(vegan_days / total_days * 100, 1),
            "daily_results": results
        }
