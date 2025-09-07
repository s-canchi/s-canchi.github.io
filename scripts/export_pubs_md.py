from scholarly import scholarly
import os

# set paths
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
output_path = os.path.join(parent_dir, "publications.md")

# scholar ID
SK_ID = "VFuny54AAAAJ"

author = scholarly.search_author_id(SK_ID)
publications = list(scholarly.fill(author, sections=['publications'])['publications'])
N = 10

md_out = "# Publications\n\n"
for pub in publications[:N]:
    pub_filled = scholarly.fill(pub)
    title = pub_filled.get("bib", {}).get("title", "Untitled")
    url = pub_filled.get("eprint_url", "") or pub_filled.get("bib", {}).get("url", "")
    # include article link if valid
    link_title = f"[{title}]({url})" if url and url.startswith("http") else title

    authors_raw = pub_filled.get("bib", {}).get("author", "")
    # split author string
    if " and " in authors_raw:
        authors_split = [a.strip() for a in authors_raw.split(" and ")]
    else:
        authors_split = [a.strip() for a in authors_raw.split(",")]
    # format name
    author_list = []
    for name in authors_split:
        parts = name.split()
        if len(parts) == 0:
            continue
        initials = " ".join([p[0] for p in parts[:-1] if len(p) > 0])
        initials_last = (initials + " " + parts[-1]).strip() if initials else parts[-1]
        author_list.append(initials_last)
    if len(author_list) > 10:
        authors = ", ".join(author_list[:10]) + ", et al."
    else:
        authors = ", ".join(author_list)

    venue = pub_filled.get("bib", {}).get("journal", "")   
    year = pub_filled.get("bib", {}).get("pub_year", "")
    citation = f"{authors} ({year}). {link_title}"
    if venue:
        citation += f". *{venue}*"
    citation += "."
    md_out += citation + "\n\n"

# add gs link 
scholar_url = f"https://scholar.google.com/citations?user={SK_ID}"
md_out += f"*Full publication list: [Google Scholar]({scholar_url})*\n"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(md_out)