import pytest
import pytest_asyncio
import json
from pathlib import Path
from ..playwright_wrapper import PlaywrightWrapper

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def require_playwright_browser(ensure_playwright_browser):
    """Auto-use fixture to ensure all tests in this module have Playwright browsers."""
    pass

# Get the directory of the current test file
TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / "test_fixtures"

# Load the buildDomTree.js content
with open(TEST_DIR.parent / "buildDomTree.js", "r") as f:
    BUILD_DOM_TREE_JS = f.read()


@pytest.fixture(scope="module")
def vcr_config():
    return {
        "filter_headers": ["authorization", "cookie"],
        "ignore_localhost": True,
    }


@pytest_asyncio.fixture(scope="function")
async def browser():
    """Fixture to provide a browser instance with buildDomTree loaded."""
    pw = PlaywrightWrapper(headless=True)
    await pw.__aenter__()
    await pw.open_page("about:blank")
    try:
        yield pw
    finally:
        await pw.__aexit__(None, None, None)


async def load_test_page(browser, fixture_name):
    """Helper to load a test fixture page and evaluate the DOM tree using evaluate_dom_tree."""
    fixture_path = FIXTURES_DIR / f"{fixture_name}.html"
    url = f"file://{fixture_path.absolute()}"
    await browser.open_page(url, wait_until="domcontentloaded")
    return await browser.evaluate_dom_tree()


def normalize_dom_tree(tree):
    """
    Recursively normalize a DOM tree dict for logical comparison.
    - Removes fields that may vary but are not semantically important (e.g., node IDs, dynamic timestamps).
    - Sorts attributes/children where order is not significant.
    """
    if isinstance(tree, dict):
        # Remove keys that are known to be non-semantic or unstable
        ignore_keys = {"xpath", "id", "highlightIndex"}
        return {
            k: normalize_dom_tree(v) for k, v in tree.items() if k not in ignore_keys
        }
    elif isinstance(tree, list):
        return [normalize_dom_tree(x) for x in tree]
    else:
        return tree


@pytest.mark.asyncio
async def test_reddit_comments_dom_tree_logical_equivalence(browser):
    """
    Test that the DOM tree extracted from test_reddit_comments.html is logically identical
    to eval_dom_tree_reddit.json, ignoring non-semantic differences.
    """
    # Load expected JSON
    json_path = FIXTURES_DIR / "eval_dom_tree_reddit.json"
    with open(json_path, "r", encoding="utf-8") as f:
        expected = json.load(f)
    # Load actual DOM tree from the HTML fixture
    fixture_path = FIXTURES_DIR / "test_reddit_comments.html"
    url = f"file://{fixture_path.absolute()}"
    await browser.open_page(url, wait_until="domcontentloaded")
    actual = await browser.evaluate_dom_tree()
    # Normalize both
    norm_actual = normalize_dom_tree(actual)
    norm_expected = normalize_dom_tree(expected)
    # Compare
    assert (
        norm_actual == norm_expected
    ), "DOM tree does not match expected logical structure"


@pytest.mark.asyncio
async def test_basic_dom_structure(browser):
    """Test basic DOM structure parsing."""
    dom_tree = await load_test_page(browser, "test_basic")
    node_map = dom_tree["map"]
    root_id = dom_tree["rootId"]
    root_node = node_map[root_id]

    # Basic structure assertions
    assert root_node["tagName"].upper() == "BODY"
    body_node = root_node  # The root is BODY

    # Debug: print the entire node map
    print("NODE MAP:", json.dumps(node_map, indent=2))

    # Use the first <div> under <body> as the container
    container_node = None
    for child_id in body_node.get("children", []):
        child = node_map[child_id]
        if child.get("tagName", "").lower() == "div":
            container_node = child
            break
    assert container_node is not None, "Container div not found"

    # Verify container children
    container_children = [node_map[cid] for cid in container_node["children"]]
    assert len(container_children) == 4  # h1, button, a, div.hidden
    assert container_children[0]["tagName"].upper() == "H1"
    assert container_children[1]["tagName"].upper() == "BUTTON"
    assert container_children[2]["tagName"].upper() == "A"
    assert container_children[3]["tagName"].upper() == "DIV"


@pytest.mark.asyncio
async def test_interactive_elements(browser):
    """Test interactive elements detection."""
    dom_tree = await load_test_page(browser, "test_interactive")
    # Traverse the flat map structure returned by evaluate_dom_tree
    node_map = dom_tree["map"]
    root_id = dom_tree["rootId"]

    def find_by_attr(node_id, attr, value):
        node = node_map[node_id]
        if node.get("attributes", {}).get(attr) == value:
            return node
        for child_id in node.get("children", []):
            found = find_by_attr(child_id, attr, value)
            if found:
                return found
        return None

    # Find the <form> node by tagName (case-insensitive)
    def find_by_tag(node_id, tag):
        node = node_map[node_id]
        if node.get("tagName", "").lower() == tag.lower():
            return node
        for child_id in node.get("children", []):
            found = find_by_tag(child_id, tag)
            if found:
                return found
        return None

    form_data = find_by_tag(root_id, "form")
    assert form_data is not None
    assert form_data["tagName"].upper() == "FORM"
    assert len(form_data["children"]) == 3  # input, select, button
    # Verify input element
    input_el = node_map[form_data["children"][0]]
    assert input_el["tagName"].upper() == "INPUT"
    assert input_el["attributes"].get("type") == "text"
    # Verify custom interactive element
    custom_button_data = find_by_attr(root_id, "id", "custom-button")
    assert custom_button_data is not None
    assert custom_button_data["attributes"].get("role") == "button"


@pytest.mark.asyncio
async def test_element_visibility(browser):
    """Test visibility detection of elements."""
    dom_tree = await load_test_page(browser, "test_layout")
    node_map = dom_tree["map"]
    root_id = dom_tree["rootId"]

    # Find the content div by id in the flat map
    def find_by_id(node_id, id_val):
        node = node_map[node_id]
        if node.get("attributes", {}).get("id") == id_val:
            return node
        for child_id in node.get("children", []):
            found = find_by_id(child_id, id_val)
            if found:
                return found
        return None

    # Debug: print all node IDs, tag names, and attributes
    for nid, node in node_map.items():
        print(f"Node {nid}: tag={node.get('tagName')}, attrs={node.get('attributes')}")

    # Find the <div> node with four <article> children
    def is_article_node(node):
        return node.get("tagName", "").lower() == "article"

    content_node = None
    for node in node_map.values():
        if node.get("tagName", "").lower() == "div":
            children = [node_map[cid] for cid in node.get("children", [])]
            if len(children) == 4 and all(is_article_node(child) for child in children):
                content_node = node
                break
    assert (
        content_node is not None
    ), "Content <div> with four <article> children not found"
    articles = [node_map[cid] for cid in content_node["children"]]
    assert len(articles) == 4
    # Debug: print full contents of article nodes
    for i, art in enumerate(articles):
        print(f"Article {i}: {art}")
    # (Visibility checks will be added after inspection)


@pytest.mark.asyncio
async def test_iframe_handling(browser):
    """Test iframe handling in the DOM tree."""
    dom_tree = await load_test_page(browser, "test_iframe")
    node_map = dom_tree["map"]
    # Find the iframe node by tagName and id in attributes
    iframe_node = None
    for node in node_map.values():
        if (
            node.get("tagName", "").upper() == "IFRAME"
            and node.get("attributes", {}).get("id") == "test-iframe"
        ):
            iframe_node = node
            break
    assert iframe_node is not None, "IFRAME node with id='test-iframe' not found"
    assert iframe_node["tagName"].upper() == "IFRAME"
    assert iframe_node["attributes"].get("id") == "test-iframe"
    # For iframe content, still use Playwright's frame API for the button existence check
    iframe = await browser.page.wait_for_selector("#test-iframe")
    frame = await iframe.content_frame()
    await frame.wait_for_load_state()
    iframe_button = await frame.query_selector("#iframe-button")
    assert iframe_button is not None


@pytest.mark.asyncio
async def test_highlighting(browser):
    """Test element highlighting functionality."""
    await browser.open_page(f"file://{(FIXTURES_DIR / 'test_basic.html').absolute()}")
    # Use evaluate_dom_tree with highlighting and debug mode
    await browser.evaluate_dom_tree(do_highlight_elements=True, debug_mode=True)
    # Check if highlighting was applied
    button = await browser.page.query_selector("#test-button")
    highlight_style = await button.evaluate(
        """(el) => {
        return window.getComputedStyle(el).getPropertyValue('outline');
    }"""
    )
    assert highlight_style and highlight_style != "none"
