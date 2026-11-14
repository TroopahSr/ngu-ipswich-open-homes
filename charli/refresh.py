#!/usr/bin/env python3
"""Rebuild /charli from the shared listings file — no network.

Reads /workspace/ngu-open-homes/data/listings-shared.json. Open homes stay
Leigh's master via sync_agent_open_homes.py after this runs.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "index.html"
SHARED = Path("/workspace/ngu-open-homes/data/listings-shared.json")
BNE = timezone(timedelta(hours=10))

def _brisbane_today():
    return datetime.now(BNE).date()

def date_label(iso: str) -> str:
    if not iso:
        return ""
    y, m, d = iso.split("-")
    mon = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return f"{int(d)} {mon[int(m)-1]} {y}"

def build_apply(current_rows, sold_photos) -> str:
    payload = {"rows": current_rows, "soldPhotos": sold_photos}
    data = json.dumps(payload, ensure_ascii=False)
    return """/* CHARLI_APPLY_START */
const CHARLI=new Set();
const CHARLI_FEED=""" + data + """;
(function(){
  const feed=CHARLI_FEED;
  for(const row of feed.rows){
    let p=P.find(x=>String(x[0])===String(row.id));
    if(!p){
      p=[row.id,row.street,row.suburb,row.price,row.beds||0,row.baths||0,row.cars||0,row.land||0,null,null,row.url,"",1,(row.media&&(row.media.gn||row.media.g)||[]).length,[],"Charli’s listing"];
      P.push(p);
    }else{
      p[3]=row.price;p[4]=row.beds||0;p[5]=row.baths||0;p[6]=row.cars||0;if(row.land)p[7]=row.land;
    }
    CHARLI.add(p[1]);
    MEDIA[String(p[0])]=row.media;
    if(row.photo)PHOTOS[String(p[0])]=row.photo;
  }
  Object.assign(PHOTOS, feed.soldPhotos);
})();
/* CHARLI_APPLY_END */"""

def patch_copy(html, n_sale, n_sold, top_price, top_i):
    html = re.sub(
        r'<p class="proof">[\s\S]*?</p>',
        f'<p class="proof"><a href="#reviews" data-scroll="reviews">About reviews</a><span><span class="sold-n">{n_sold}</span> sales in 12 months</span><a href="#sold-{top_i}">Top sale {top_price}</a></p>',
        html,
        count=1,
    )

    html = html.replace(
        '<p class="proof"><a href="#reviews" data-scroll="reviews">Client testimonials</a><span>5 recent sales featured</span><a href="#sold-0">Top sale $1,000,000</a></p>',
        f'<p class="proof"><a href="#reviews" data-scroll="reviews">Client testimonials</a><span><span class="sold-n">{n_sold}</span> sales in 12 months</span><a href="#sold-{top_i}">Top sale {top_price}</a></p>',
    )
    html = html.replace(
        "<p class=\"lead\">5 recent sales featured below.</p>",
        f"<p class=\"lead\"><span class=\"sold-n\">{n_sold}</span> sales in the last 12 months, including joint sales. The latest are below.</p>",
    )
    html = html.replace(
        "<p class=\"lead\">5 recent sales.</p>",
        f"<p class=\"lead\"><span class=\"sold-n\">{n_sold}</span> sales in the last 12 months where Charli is named, including joint sales.</p>",
    )
    html = html.replace(
        '<p class="count" style="margin-top:24px">Sales and prices from ngurealestate.com.au, checked 2 November 2026. Sales shown are from Charli Grace’s public NGU listings. Legacy note removed from realestate.com.au.</p>',
        '<p class="count" style="margin-top:24px">Prices and sold dates from <a class="link" href="https://view.com.au/agent-profile/charli-grace-210613/" target="_blank" rel="noopener">view.com.au</a>, checked 7 November 2026, for sales since 7 November 2024. Photos are full-size images from NGU’s Rex library (the same source as the rest of this site), or view.com.au where NGU has no gallery. realestate.com.au did not return a personal rating.</p>',
    )
    html = html.replace(
        '<p class="stars" role="img" aria-label="5 out of 5 stars">★★★★★</p>\n      <blockquote>',
        '<p class="who">Testimonials published by NGU Real Estate. No personal star rating is shown: realestate.com.au and RateMyAgent did not return Charli’s own rating or review count when checked on 7 November 2026.</p>\n      <blockquote>',
    )
    html = html.replace(
        '<p class="pu-proof">★ 4.8 from 16 reviews · “…extremely knowledgeable of the industry and market conditions.” Seller, Flinders View</p>',
        "",
    )
    # home tile caption is static and fine. Sale count is computed.
    html = html.replace(
        "PLACEHOLDER_FOOTER_WILL_NOT_MATCH",
        f"Charli listings and sales refreshed {CHECKED} from view.com.au and ngurealestate.com.au. {n_sale} for sale, {n_sold} sales since {date_label(WINDOW_START)}.",
    )
    html = re.sub(r'<span class="sold-n">\d+</span>', f'<span class="sold-n">{n_sold}</span>', html)
    html = re.sub(r"\d+ sales since \d{1,2} \w+ \d{4}\.", f"{n_sold} sales since {date_label(WINDOW_START)}.", html)
    since = date_label(WINDOW_START)
    html = re.sub(r"(checked )\d{1,2} \w+ \d{4}", rf"\g<1>{CHECKED}", html)
    html = re.sub(r"(for sales since )\d{1,2} \w+ \d{4}", rf"\g<1>{since}", html)
    html = re.sub(r"(sales since )\d{1,2} \w+ \d{4}", rf"\g<1>{since}", html)
    return html


def ensure_empty_state(html: str) -> str:
    """Keep Open homes empty-state wording aligned with Leigh (opens still synced later)."""
    old_empty = 'if(!DAYS.length){$("oh-h1").textContent="Open homes.";$("oh-list").innerHTML=`<div class="empty">No upcoming open homes right now. New opens are added through the week. <a class="link" href="#for-sale">Browse homes for sale</a></div>`;$("count").textContent="";return}'
    new_empty = (
        'if(!DAYS.length){$("oh-h1").textContent="Open homes.";'
        'const W=(typeof OH_DAYS!=="undefined"?OH_DAYS:[]).filter(d=>d>=todayISO).map(d=>'
        '{const t=new Date(d+"T00:00:00Z");return DOWL[t.getUTCDay()]+" "+t.getUTCDate()+" "+MONL[t.getUTCMonth()]});'
        'const wk=W.length?W.join(" and ").replace(/ (\\w+) and (\\w+ \\d+ )\\1$/," and $2$1"):"";'
        '$("oh-list").innerHTML=`<div class="empty">${wk?`No open homes listed yet for ${esc(wk)}.`:"No open homes listed yet."} Check back soon.</div>`;'
        '$("count").textContent="";document.querySelector("#v-open-homes .oh-tools").hidden=true;return}'
    )
    if old_empty in html:
        html = html.replace(old_empty, new_empty, 1)
    return html

def main():
    if not SHARED.exists():
        print(f"ERROR: missing {SHARED} — run scripts/crawl_agent_listings.py first", file=sys.stderr)
        return 1
    data = json.loads(SHARED.read_text(encoding="utf-8"))
    agent = (data.get("agents") or {}).get("charli")
    if not agent:
        print("ERROR: listings-shared.json has no agents.charli", file=sys.stderr)
        return 1

    global CHECKED, WINDOW_START
    CHECKED = data.get("checkedLabel") or _brisbane_today().strftime("%-d %B %Y")
    WINDOW_START = data.get("windowStart") or agent.get("windowStart") or ""

    current_rows = agent["forSale"]
    sold_items = agent["sold"]
    sold_rows = [x["row"] for x in sold_items]
    sold_meta = {x["row"][8]: x["meta"] for x in sold_items}
    sold_photos = {("s" + str(i)): x["photo"] for i, x in enumerate(sold_items) if x.get("photo")}

    html = HTML_PATH.read_text(encoding="utf-8")
    m = re.search(r"const SOLD_META=(\{.*?\});", html, re.S)
    if m:
        try:
            old_meta = json.loads(m.group(1))
        except Exception:
            old_meta = {}
        for k, meta in sold_meta.items():
            if not meta.get("d") and old_meta.get(k, {}).get("d"):
                meta["d"] = old_meta[k]["d"]

    top_i = agent.get("topSaleIndex", 0)
    top_price = agent.get("topSalePrice") or (sold_rows[top_i][2] if sold_rows else "")
    n_sale = len(current_rows)
    n_sold = len(sold_rows)
    print(f"charli offline rebuild from {SHARED.name}: forSale {n_sale} sold {n_sold} top {top_price}", flush=True)

    sold_js = "const SOLD=" + json.dumps(sold_rows, ensure_ascii=False) + ";\nconst SOLD_META=" + json.dumps(sold_meta, ensure_ascii=False) + ";"
    sold_block = "/* CHARLI_SOLD_START */\n" + sold_js + "\n/* CHARLI_SOLD_END */"
    if "/* CHARLI_SOLD_START */" in html:
        html = re.sub(r"/\* CHARLI_SOLD_START \*/[\s\S]*?/\* CHARLI_SOLD_END \*/", lambda _m: sold_block, html, count=1)
    else:
        html = re.sub(r"const SOLD=\[[\s\S]*?const PHOTOS=", sold_block + "\nconst PHOTOS=", html, count=1)

    apply = build_apply(current_rows, sold_photos)
    if "/* CHARLI_APPLY_START */" in html:
        html = re.sub(r"/\* CHARLI_APPLY_START \*/[\s\S]*?/\* CHARLI_APPLY_END \*/", lambda _m: apply, html, count=1)

    html = patch_copy(html, n_sale, n_sold, top_price, top_i)
    html = html.replace(
        '<link rel="preconnect" href="https://au-crm.cdns.rexsoftware.com" crossorigin>',
        '<link rel="preconnect" href="https://au-crm.cdns.rexsoftware.com" crossorigin>\n<link rel="preconnect" href="https://view.com.au" crossorigin>',
        1,
    )
    old_specs = '<span class="specs"><span><b>${x[4]}</b> bed</span><span><b>${x[5]}</b> bath</span>'
    new_specs = '<span class="specs">${x[4]?`<span><b>${x[4]}</b> bed</span>`:""}${x[5]?`<span><b>${x[5]}</b> bath</span>`:""}'
    if old_specs in html:
        html = html.replace(old_specs, new_specs, 1)
    old_fine = "Result from NGU Real Estate. Corey can walk you through the comparable sales nearby."
    new_fine = "Sold price and date from view.com.au. Photos are the full-size NGU images where Charli is named on the listing."
    html = html.replace(old_fine, new_fine)
    # Do NOT sync opens here — Leigh master via sync_agent_open_homes.py
    html = ensure_empty_state(html)
    HTML_PATH.write_text(html, encoding="utf-8")
    print("wrote", HTML_PATH, flush=True)
    return 0

CHECKED = _brisbane_today().strftime("%-d %B %Y")
WINDOW_START = ""

if __name__ == "__main__":
    raise SystemExit(main())
