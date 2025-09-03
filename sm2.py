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
                I = I * EF
            n += 1
        else: # (incorrect response)
            n = 0
            I = 1

        EF = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        if EF < 1.3:
            EF = 1.3
        
        return n, EF, I
        