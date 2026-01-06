# Coin Game: Make Exactly One Dollar

while True:
    print("Enter the number of each coin type:")
    pennies = int(input("Number of pennies: "))
    nickels = int(input("Number of nickels: "))
    dimes = int(input("Number of dimes: "))
    quarters = int(input("Number of quarters: "))
    
    # Calculate total value in dollars
    total = pennies * 0.01 + nickels * 0.05 + dimes * 0.10 + quarters * 0.25
    
    # Check the total
    if total == 1.00:
        print("Congratulations! You won the game!")
        break
    elif total < 1.00:
        print(f"The total amount ${total:.2f} is less than $1.00. Try again.\n")
    else:
        print(f"The total amount ${total:.2f} is more than $1.00. Try again.\n")