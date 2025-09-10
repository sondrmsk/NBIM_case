The workflow for the dividend reconcialiation is as follows:

1. The diagnoser assumes the datasets have the same structure, merges them with the relevant fields (dropping all fields that only occur in one of the datasets, as this is irrelevant) and classifies all the dividend occasions, from none (nothing to worry about) to high (much to worry about). The agent can alaso, if it feels that it needs more context, 
    -An improvement here would be to get the agent to not assume the same structure, and actually identify the relevant or common fields. This is sort of what we have done to reach the standardized fields.
2. The remediator then takes all issues that are medium or higher and uses its RAG-abilities with the knowledge base containing previous mismatches/problems to suggest fixes. The fixes suggested will then, if approved, be added to either the original datasets or the new dataset.
3. The remediation_approver takes all accepted remediations and stores them in what is now the approved_remediations.json, but at a later point will be into the knowledge base.
4. At the end, an e-mail agent sendsa an automatic e-mail to the custodian, notifying therm of the discrepancies




Future work:
    -Automatical reading of settlements each EOD
    -Validation agent that parses through changes
    -A general agent that looks for "bigger picture" errors or challenges by analyzing the original datasets. This was not implemented now due to time and the lack of understanding for why we need it from my viewing of the test set.
    -A more mathematical approach linking different fields together and sum_checks for connected fields (e.g. holding + loaned = total holding). Again, was not implemented, du to a lack of understanding for how the fields were actually connected, calculated etc. This could have been a tool for the diagnoser agent.
    -Other remediation possibilities:
        -Rule-based system (more deterministic)
        -Machine Learning
        -Optimization-based, e.g. simplex alogrithm trying to minimize discrepancy between NBIM and CUSTODY
        -Expert training, making the agent an expert by training it and teaching it in dividend payout reconciliation