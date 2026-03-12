# 레이팅 계산 로직 (서비스 함수)
def calculate_rating_change(current_rating: int, is_correct: bool):
    K = 32  # 점수 변동의 기본 폭 (스타크래프트의 K-Factor와 유사)
    
    if is_correct:
        # 정답 시: 1000점 기준 약 32점 상승
        new_rating = current_rating + K
    else:
        # 오답 시: 약 20점 하락 (상승폭보다 적게 잡아서 유저의 의욕을 유지)
        new_rating = current_rating - 20
        
    # 레이팅 하한선 설정 (예: 800점 밑으로는 안 내려감)
    return max(800, new_rating)