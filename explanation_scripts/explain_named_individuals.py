"""
Script to show the difference between Named Individuals and regular class instances
"""

print("=" * 80)
print("DIFFERENCE: Named Individuals vs Regular Class Instances")
print("=" * 80)
print()

print("1. REGULAR CLASS INSTANCE (without owl:NamedIndividual):")
print("-" * 80)
print("""
<http://example.org/mortgage_loan/L-000001> a ex:MortgageLoan ;
    ex:principalAmount 221958 ;
    ex:interestRate 0.0657 .
""")

print("2. OWL NAMED INDIVIDUAL (with owl:NamedIndividual):")
print("-" * 80)
print("""
<http://example.org/mortgage_loan/L-000001> a ex:MortgageLoan, owl:NamedIndividual ;
    ex:principalAmount 221958 ;
    ex:interestRate 0.0657 .
""")

print("=" * 80)
print("KEY DIFFERENCES:")
print("=" * 80)
print()

differences = [
    ("Semantic Meaning",
     "Just states 'this is a MortgageLoan'",
     "Explicitly declares 'this is a specific, named individual of type MortgageLoan'"),

    ("OWL Reasoning",
     "Basic type inference only",
     "Full OWL reasoning - distinct from anonymous individuals and classes"),

    ("OWL2 Compliance",
     "May not validate in strict OWL2 tools",
     "Required for OWL2 DL profile compliance"),

    ("Ontology Design",
     "Informal assertion",
     "Formal ontology commitment - explicit ABox (assertions)"),

    ("Closed World",
     "Assumes what's not stated is unknown",
     "Makes explicit 'unique name assumption' - this IS a real entity"),

    ("Tool Support",
     "Works in basic RDF tools",
     "Required for Protégé, HermiT, Pellet reasoners, SWRL rules"),
]

for i, (aspect, without, with_owl) in enumerate(differences, 1):
    print(f"{i}. {aspect}:")
    print(f"   WITHOUT: {without}")
    print(f"   WITH:    {with_owl}")
    print()

print("=" * 80)
print("WHEN TO USE owl:NamedIndividual:")
print("=" * 80)
print()
uses = [
    "✓ Building formal ontologies for research or standardization",
    "✓ Using OWL reasoners (Pellet, HermiT, FaCT++) for inference",
    "✓ Implementing SWRL rules or SHACL constraints",
    "✓ Publishing Linked Open Data with strict OWL2 compliance",
    "✓ Integrating with Protégé or other ontology editors",
    "✓ Distinguishing named entities from blank nodes",
    "✓ Ensuring compatibility with semantic web validators"
]

for use in uses:
    print(f"  {use}")

print()
print("=" * 80)
print("STATISTICS FROM YOUR TRANSFORMATION:")
print("=" * 80)
print()
print(f"  • Without owl:NamedIndividual: 6,500,000 triples")
print(f"  • With owl:NamedIndividual:    8,000,000 triples")
print(f"  • Additional triples:          1,500,000 (23% increase)")
print(f"  • Entities declared:           1,500,000 (500k loans + 500k borrowers + 500k properties)")
print()
print("=" * 80)

