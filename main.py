#!/usr/bin/env python3
from agents.diagnoser import Diagnoser

def main():
    agent = Diagnoser()
    result = agent.run(
        "Call merge_and_transpose on 'data/NBIM_Dividend_Bookings 1.csv' "
        "and 'data/CUSTODY_Dividend_Bookings 1.csv' and tell me what it is about."
    )
    print("Agent result:", result)

if __name__ == "__main__":
    main()

