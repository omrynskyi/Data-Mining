Project 04: Associative Pattern Mining Studio

WHAT IT IS
A market basket analysis system. It mines retail transaction data for association rules, like "customers who buy A also tend to buy B," using the FP-Growth algorithm, then shows the rules in an interactive Flask dashboard.

HOW TO RUN
Command: make 04   (or ./run --04)
Opens at: http://localhost:5050

FILES TO SHOW ON SCREEN
1. src/mining/engine.py - runs FP-Growth and generates the rules
2. app.py - the Flask dashboard server

CODE - src/mining/engine.py (mining core)

def mine_frequent_itemsets(df_onehot, min_support, algorithm, max_len, engine):
    if algorithm == "apriori":
        itemsets_df = apriori(df_onehot, min_support=min_support, max_len=max_len, use_colnames=True)
    else:
        itemsets_df = fpgrowth(df_onehot, min_support=min_support, max_len=max_len,
                                use_colnames=True, engine=engine)
    return itemsets_df

def mine_association_rules(df_onehot, min_support=0.01, min_confidence=0.3,
                            metric="lift", min_metric_val=1.2, max_len=4, algorithm="fpgrowth"):
    itemsets_df = mine_frequent_itemsets(df_onehot, min_support, algorithm, max_len, engine="auto")
    rules_df = generate_association_rules(
        frequent_itemsets_df=itemsets_df,
        min_confidence=min_confidence,
        metric=metric,
        min_metric_val=min_metric_val,
    )
    return itemsets_df, rules_df

Explain the two step process: first find frequent itemsets, groups of items that appear together often enough to pass the min_support threshold. Then turn those itemsets into if-then rules, keeping only the ones that pass the min_confidence and lift thresholds.

SCRIPT

Intro, 0:00 to 0:25
Say you are showing Project 04, the associative pattern mining studio.
Launch it with make 04.
Mention Flask is configured to run on port 5050 specifically to avoid a conflict with macOS AirPlay, which also uses port 5000.

Code walkthrough, 0:25 to 1:15
Open src/mining/engine.py.
Explain the two stage process: mine_frequent_itemsets finds item combinations that occur often enough in the transaction data, using FP-Growth. Then mine_association_rules turns those into rules and filters them by confidence and lift.
Mention that a custom redundancy pruning step removes rules that add nothing new, bringing 2,225 transaction baskets down to 626 useful high lift rules.

Live demo, 1:15 to 2:00
Switch to the browser at localhost 5050.
Show the table of association rules, the support versus lift scatter plot, and the rule network graph.
Use the interactive sandbox to add items to a basket and show live rule recommendations.

Wrap up
This concludes Project 04.
