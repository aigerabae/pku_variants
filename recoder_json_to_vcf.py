#!/usr/bin/env python3
"""
Convert Ensembl Variant Recoder JSON output into VCF format
matching the Recoder's own --accept text/x-vcf output style.

Usage:
    python3 recoder_json_to_vcf.py input.json output.vcf
"""

import json
import sys


HEADER = """##fileformat=VCFv4.2
##Variant Recoder
##API version 115
##INFO=<ID=HGVSg,Number=.,Type=String,Description="HGVS Genomic">
##INFO=<ID=HGVSc,Number=.,Type=String,Description="HGVS Transcript">
##INFO=<ID=HGVSp,Number=.,Type=String,Description="HGVS Protein">
##INFO=<ID=SPDI,Number=.,Type=String,Description="HGVS Genomic">
##INFO=<ID=VARID,Number=.,Type=String,Description="Variant identifier is the ID of variants present in the Ensembl Variation database that are co-located with input">
##INFO=<ID=VCF,Number=.,Type=String,Description="VCF string">
##INFO=<ID=Variant_synonyms,Number=.,Type=String,Description="Extra known synonyms for co-located variants">
##INFO=<ID=MANE_Select,Number=.,Type=String,Description="MANE Select (Matched Annotation from NCBI and EMBL-EBI) Transcripts">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
"""

# JSON field -> VCF INFO key, in the order they should appear
FIELD_MAP = [
    ("hgvsg", "HGVSg"),
    ("hgvsc", "HGVSc"),
    ("hgvsp", "HGVSp"),
    ("spdi", "SPDI"),
    ("id", "VARID"),
    ("vcf_string", "VCF"),
    ("synonyms", "Variant_synonyms"),
    ("mane_select", "MANE_Select"),
]


def build_info(allele_data: dict) -> str:
    parts = []
    for json_key, info_key in FIELD_MAP:
        values = allele_data.get(json_key)
        if values:
            parts.append(f"{info_key}=" + ",".join(values))
    return ";".join(parts) + (";" if parts else "")


def convert(data) -> list:
    # Some Recoder JSON dumps are a list of per-variant objects; a single
    # lookup can also come back as one bare dict rather than a list.
    if isinstance(data, dict):
        data = [data]

    rows = []
    skipped = 0
    for variant_entry in data:
        # Failed/unresolved IDs can come back as null in the list, or as
        # {"error": "..."} instead of the usual allele-keyed dict.
        if not isinstance(variant_entry, dict):
            skipped += 1
            continue
        if "error" in variant_entry:
            skipped += 1
            continue

        # each top-level dict is keyed by ALT allele (e.g. "T", "A", "-")
        for allele, allele_data in variant_entry.items():
            if not isinstance(allele_data, dict):
                continue
            vcf_strings = allele_data.get("vcf_string")
            if not vcf_strings:
                continue  # skip alleles Recoder couldn't place on the genome

            for vcf_str in vcf_strings:
                chrom, pos, ref, alt = vcf_str.split("-")
                ids = allele_data.get("id", [])
                vcf_id = ids[0] if ids else "."
                info = build_info(allele_data)
                rows.append(
                    f"{chrom}\t{pos}\t{vcf_id}\t{ref}\t{alt}\t.\t.\t{info}"
                )

    if skipped:
        print(f"Skipped {skipped} unresolved/error entr{'y' if skipped == 1 else 'ies'}", file=sys.stderr)

    return rows


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.json output.vcf", file=sys.stderr)
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]

    with open(in_path) as f:
        data = json.load(f)

    rows = convert(data)

    with open(out_path, "w") as f:
        f.write(HEADER)
        f.write("\n".join(rows))
        f.write("\n")

    print(f"Wrote {len(rows)} record(s) to {out_path}")


if __name__ == "__main__":
    main()
