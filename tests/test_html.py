import http.server
import random
import socketserver
from multiprocessing import Process
from pathlib import Path

import pytest
from great_tables import GT
from great_tables.data import exibble
from playwright.sync_api import expect, sync_playwright

test_schema = "http"
test_hostname = "127.0.0.1"
test_port = random.randint(8500, 8999)
test_url = f"{test_schema}://{test_hostname}:{test_port}/"


title = "title"
subtitle = "subtitle"
stubhead = "stubhead"
spanner = "spanner"
spanner_columns = ["date", "time", "datetime"]
source_note = "source_note"
columns = exibble.columns.to_list()
columns.remove("group")  # using in tab_stub
columns.remove("row")  # using in tab_stub


def run_server():
    with socketserver.TCPServer(
        (test_hostname, test_port), http.server.SimpleHTTPRequestHandler
    ) as httpd:
        httpd.serve_forever()


@pytest.fixture(scope="module", autouse=True)
def start_server():
    process = Process(target=run_server, daemon=True)
    process.start()
    yield
    process.terminate()


@pytest.fixture(scope="module")
def gtbl_html():
    return (
        GT(exibble)
        .tab_stub(groupname_col="group", rowname_col="row")
        .tab_stubhead(stubhead)
        .tab_spanner(spanner, columns=spanner_columns)
        .tab_header(title=title, subtitle=subtitle)
        .tab_source_note(source_note)
    ).as_raw_html()


@pytest.fixture(scope="module")
def html_content(gtbl_html):
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    {}
</body>
</html>
""".format(gtbl_html)


@pytest.fixture(scope="module", autouse=True)
def write_index_html(html_content):
    index_html = Path("index.html")
    index_html.write_text(html_content, encoding="utf-8")
    yield
    index_html.unlink()


@pytest.mark.parametrize("core", ["chromium", "firefox"])
def test_page(core):
    with sync_playwright() as p:
        browser = getattr(p, core).launch(headless=True)
        page = browser.new_page()
        page.goto(test_url)

        # page.screenshot(path="table.png")

        # group
        group_loc = page.locator("tr:has(th.gt_group_heading)").first
        expect(group_loc).to_have_text("grp_a")

        # row
        row_1_loc = page.locator(".gt_stub").first
        expect(row_1_loc).to_have_text("row_1")

        # stubhead
        stubhead_loc = page.locator("#stubhead")
        expect(stubhead_loc).to_have_text(stubhead)

        # spanner
        spanner_loc = page.locator(".gt_column_spanner")
        expect(spanner_loc).to_have_text(spanner)

        for s_col in spanner_columns:
            spanner_col_loc = page.locator(f"#{s_col}")
            rowspan = spanner_col_loc.get_attribute("rowspan")
            assert rowspan == "1"

        # title
        title_loc = page.locator(".gt_title")
        expect(title_loc).to_have_text(title)

        # subtitle
        subtitle_loc = page.locator(".gt_subtitle")
        expect(subtitle_loc).to_have_text(subtitle)

        # sourcenote
        sourcenote_loc = page.locator(".gt_sourcenote")
        expect(sourcenote_loc).to_have_text(source_note)

        # columns
        for column in columns:
            column_loc = page.locator(f"#{column}")
            expect(column_loc).to_have_text(column)

        browser.close()
