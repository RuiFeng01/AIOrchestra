import spacy
import re

# Load spaCy model
print("Loading model...")
nlp = spacy.load("en_core_web_lg")

# Custom component to detect additional patterns
@spacy.Language.component("custom_pii_detector")
def custom_pii_detector(doc):
    patterns = [
        (r"[STFG]\d{7}[A-Z]", "NRIC"),
        (r"Employee ID:? ?[A-Z0-9]+", "EMPLOYEE_ID"),
        (r"Case Ref:? ?[A-Za-z0-9-]+", "CASE_REF"),
        (r"Client ID #?\d+", "CLIENT_ID"),
        (r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b", "DATE"),
        (r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b", "DATE"),
        (r"\b\d{1,2} [A-Za-z]+ \d{4}\b", "DATE"),
        (r"\b[A-Z]{3} ?\d+(\.\d+)?[KMB]?\b", "AMOUNT"),  # e.g., SGD 500K, USD 2.3M
        (r"\$\d+(\.\d+)?( million| billion)?", "AMOUNT"),
        (r"\d{2,4} [\w\s]+,? \#?\d{1,4}-?\d{1,4},? \w+ \d{6}", "ADDRESS"),
        #(r"\+?\d{2,3} ?\d{4} ?\d{4}", "PHONE"),
        #(r"\+?\d{2,3} \d{8}", "PHONE"),
        #(r"\+\d{1,4} ?\d{4} ?\d{4}", "PHONE NUMB"), 
        (r"\+\d{1,4} ?\d{4} ?\d{4}", "PHONE NUMB"), 
        (r"\d{6}", "POSTALCODE"),
    ]

    existing_ents = list(doc.ents)
    new_ents = []

    for pattern, label in patterns:
        for match in re.finditer(pattern, doc.text):
            start, end = match.span()
            span = doc.char_span(start, end, label=label, alignment_mode="contract")
            if span is not None:
                new_ents.append(span)


    all_ents = existing_ents + new_ents
    all_ents.sort(key=lambda ent: ent.start_char)

    # Filter out overlapping spans to avoid ValueError (E1010)
    
    unwanted_labels = {"CARDINAL"}

    # Combine existing and new regex entities
    all_ents = existing_ents + new_ents
    all_ents.sort(key=lambda ent: ent.start_char)

    # Filter out unwanted labels and overlaps
    filtered_ents = []
    last_end = -1
    for ent in all_ents:
        if ent.label_ not in unwanted_labels and ent.start_char >= last_end:
            filtered_ents.append(ent)
            last_end = ent.end_char

    doc.set_ents(filtered_ents)
    return doc



# Add the custom PII detector to the pipeline after NER
nlp.add_pipe("custom_pii_detector", after="ner")

# Your input text (inserted as `text`)
text = '''
INTERNAL MEMORANDUM
Subject: Q2 Strategic Review – Executive Summary
Date: April 24, 2024
Prepared by: Tan Mei Ling, VP of Strategic Operations

This document is intended for internal distribution only. Do not disseminate without written approval from the Office of Corporate Counsel.

During Q2 of FY2024, Singapore Holdings Pte Ltd, headquartered at 123 Orchard Road, #12-345, Singapore 238888, experienced a 12.8% increase in gross revenue compared to Q1, driven largely by the successful integration of the Tech Solutions acquisition finalized on February 16, 2024. Total consolidated revenue reached SGD 187.4 million, up from SGD 166.1 million the previous quarter.

Key performance drivers included:

- Strong B2B sales in the Asia-Pacific region, particularly with Client ID #5472 (a large electronics supplier based in Singapore).
- Cost optimizations in the logistics and procurement divisions (led by Lim Wei Ming, Director of Supply Chain Strategy), which reduced Q2 operational expenditures by 7.4%.
- Successful rollout of the Zephyr CRM Platform to our Tier 1 enterprise clients, improving client engagement metrics by 28%.

However, several risk factors were also identified:

- The breach of NDA terms by a former employee, Sarah L. Denning (Employee ID: 1027A, NRIC: S1234567A), who allegedly shared sensitive onboarding documentation with a direct competitor, Benton & Wiles Consulting Group. Legal action is underway (Case Ref: LHI-vs-BWG-2024-0421).
- Delays in the launch of Project Orion, initially scheduled for April 1, now postponed to July 15, 2024, due to unresolved API integration issues with our overseas development partner, RedVine Technologies (Singapore).
- Declining renewal rates among small-cap clients in the Southeast Asia region, attributed in part to pricing model inconsistencies and gaps in client support responsiveness.

The Q2 Executive Steering Committee, chaired by CEO Robert M. Ellis and including CFO Janine Chau and COO Mitchell Klein, has recommended the following actions:

1. Immediate revision of the pricing matrix for all contracts below SGD 500K annual value.
2. Confidential retraining program for all Tier 2 sales staff, to be conducted by Lumen Advisory Group, beginning May 6, 2024.
3. Temporary suspension of hiring for all non-critical roles until September 2024, with exceptions reviewed by HR Director Anika Kapoor.

This document is classified as INTERNAL CONFIDENTIAL under Company Policy § 3.1.6 and should be stored in the secure SharePoint directory: /Strategy/Internal/FY2024/Q2/. Violation of confidentiality protocols may result in disciplinary action or legal proceedings.

Contact Information:
- Tan Mei Ling: +65 9123 4567
- Lim Wei Ming: +65 8234 5678
'''

# Process the text
doc = nlp(text)



# Track spans to redact
redact_spans = []

# Add detected entities
for ent in doc.ents:
    redact_spans.append((ent.start_char, ent.end_char, ent.label_))

# Add only PERSON entities as names
for ent in doc.ents:
    if ent.label_ == "PERSON":
        redact_spans.append((ent.start_char, ent.end_char, "NAME"))

# Deduplicate and sort spans
redact_spans = list(set(redact_spans))
redact_spans.sort(key=lambda x: x[0])

# Merge overlapping spans
merged_spans = []
for start, end, label in redact_spans:
    if merged_spans and merged_spans[-1][1] >= start:
        merged_start, merged_end, merged_label = merged_spans.pop()
        merged_spans.append((merged_start, max(merged_end, end), merged_label))
    else:
        merged_spans.append((start, end, label))

# Optional: dictionary can be removed if you include label directly in mask
redacted_text = text
for start, end, label in reversed(merged_spans):
    redacted_text = redacted_text[:start] + f"[{label}]" + redacted_text[end:]

# 🔍 Optional: print what was detected
print("\nDetected Entities:")
for start, end, label in merged_spans:
    print(f"{label}: {text[start:end]}")

# Output
print("\n🔍 Original Text:\n", text)
print("\n🛡️ Redacted Text:\n", redacted_text)
