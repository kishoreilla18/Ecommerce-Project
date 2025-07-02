# import random
# def genotp():
#     otp=""
#     l1=[chr(i) for i in range(ord('A'),ord('Z')+1)]
#     l2=[chr(i) for i in range(ord('a'),ord('z')+1)]
#     for i in range(0,2):
#         otp=otp+random.choice(l1)
#         otp=otp+random.choice(l2)
#         otp=otp+str(random.randint(0,9))
#     return otp

import random
def genotp():
    otp=""
    for i in range(0,6):
        otp=otp+str(random.randint(0,9))
    return otp
    
