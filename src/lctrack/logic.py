from typing import Tuple

EASE_INIT = 2.5

def SM2(q : int,
        n : int, 
        EF : float,
        I : int) -> Tuple[int, float, int]:

        if q >= 3: # (correct response)
            if n == 0:
                I = 1
            elif n == 1:
                I = 6
            else:
                I = round(I * EF)
            n += 1
        else: # (incorrect response)
            n = 0
            I = 1

        EF = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if EF < 1.3:
            EF = 1.3
        
        return n, EF, I
        
def calculate_new_state(n : int, ef : float, i : int, confidence : int, now_ts : int) -> Tuple[int, float, int, int]:
    """ 
    """
    assert 0 <= confidence <= 5, "Confidence must be in range (0-5)"

    n, ef, i = SM2(confidence, n, ef, i)

    next_review_at = now_ts + (i * 86400)

    return n, ef, i, next_review_at







    