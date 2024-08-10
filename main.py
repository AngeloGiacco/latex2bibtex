import re
import json
from exa import Exa
import requests
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase


def extract_citations(latex_content):
    citation_pattern = r"\\cite{([^}]*)}"
    return re.findall(citation_pattern, latex_content)


def get_citation_context(latex_content, citation, context_size=100):
    citation_pattern = r"\\cite{" + re.escape(citation) + r"}"
    match = re.search(citation_pattern, latex_content)
    if match:
        start = max(0, match.start() - context_size)
        end = min(len(latex_content), match.end() + context_size)
        context = latex_content[start:end]

        left_context = context[: match.start() - start]
        right_context = context[match.end() - start :]
        left_citation = re.search(r"\\cite{", left_context[::-1])
        if left_citation:
            left_context = left_context[-left_citation.start() :]
        right_citation = re.search(r"\\cite{", right_context)
        if right_citation:
            right_context = right_context[: right_citation.start()]

        return left_context + citation_pattern + right_context
    return ""


def search_exa_api(citation, context):
    exa = Exa(api_key="be68f0d7-bc15-47dc-b873-201a3b17f97f")
    result = exa.search_and_contents(
        f"{citation} {context}",
        type="neural",
        use_autoprompt=True,
        num_results=10,
        text=True,
        category="research paper",
        include_domains=["arxiv.org"],
    )
    return result


def arxiv_to_bibtex(arxiv_id):
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    response = requests.get(url)
    if response.status_code == 200:
        xml = response.text
        title = re.search(r"<title>(.*?)</title>", xml).group(1)
        authors = re.findall(r"<name>(.*?)</name>", xml)
        year = re.search(r"<published>(\d{4})", xml).group(1)
        month = re.search(r"<published>\d{4}-(\d{2})", xml).group(1)
        abstract = (
            re.search(r"<abstract>(.*?)</abstract>", xml, re.DOTALL).group(1).strip()
        )

        bibtex = f"@article{{{arxiv_id},\n"
        bibtex += f"  Author = {{{' and '.join(authors)}}},\n"
        bibtex += f"  Title = {{{title}}},\n"
        bibtex += f"  Year = {{{year}}},\n"
        bibtex += f"  Month = {{{month}}},\n"
        bibtex += f"  Eprint = {{{arxiv_id}}},\n"
        bibtex += "  ArchivePrefix = {arXiv},\n"
        bibtex += f"  Abstract = {{{abstract}}}\n"
        bibtex += "}"
        return bibtex
    return None


def process_latex_file(latex_file_path, bib_file_path):
    # Read existing BibTeX file
    with open(bib_file_path, "r") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    existing_entries = {entry["title"].lower(): entry for entry in bib_database.entries}

    # Read LaTeX file
    with open(latex_file_path, "r") as file:
        latex_content = file.read()

    citations = extract_citations(latex_content)
    new_entries = []

    for citation in citations:
        context = get_citation_context(latex_content, citation)
        exa_results = search_exa_api(citation, context)

        if exa_results and exa_results["results"]:
            first_result = exa_results["results"][0]
            title = first_result["title"].lower()

            if title not in existing_entries:
                arxiv_id = first_result["id"].split("/")[-1]
                bibtex_entry = arxiv_to_bibtex(arxiv_id)
                if bibtex_entry:
                    new_entries.append(bibtex_entry)

    # Combine existing and new entries
    combined_bibtex = "\n\n".join(
        [entry.get("bibtex", "") for entry in bib_database.entries] + new_entries
    )

    # Write combined BibTeX to file
    with open(bib_file_path, "w") as bibtex_file:
        bibtex_file.write(combined_bibtex)


# Example usage
latex_file_path = "path/to/your/latex/file.tex"
bib_file_path = "path/to/your/references.bib"
process_latex_file(latex_file_path, bib_file_path)
print(f"Updated BibTeX file saved to {bib_file_path}")
