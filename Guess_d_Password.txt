import random

n = int(input("\nEnter code length: "))

sys_code = random.randint(10**(n - 1), 10**n - 1)

for i in range(100):
    countc=0
    countp=0
    y=sys_code
    code=[]
    inp=[]

    for x in range(n):
        code.insert(x,y%10)
        y=int(y/10)
        
    code.reverse()

    num = int(input(f"\nEnter your {n}-digit guess: "))

    for x in range(n):
        inp.insert(x,num%10)
        num=int(num/10)
    inp.reverse()
    
    for x in range(n):
        if(code[x]==inp[x]):
            countp=countp+1
            
    print("\nMatching Place(s):", countp)
    
    code1=code
    
    for x in range(0,n):
        for z in range(0,n):
            if(code1[x]==inp[z]):
                countc=countc+1
                code1[x]=[10]
                inp[z]=[11]
                
    print("Matching Character(s):", countc)
    
    if(countc==n and countp==n):
        print("\nCongratulations!")
        break
        
    if(countc!=n or countp!=n):
        print("\nPlease try again!")
