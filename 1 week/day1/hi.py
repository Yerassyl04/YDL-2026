name = input("What is your name? ")
date = input("What is your birthday year? ")

if date.isdigit():
    print(f"Hello {name}, you were born in {date}.")
    print("You are", 2026 - int(date), "years old.")
else:
    print("Please enter a valid year.")