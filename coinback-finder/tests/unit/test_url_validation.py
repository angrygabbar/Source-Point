import pytest

from app.discovery.url_validation import UrlValidationError, validate_flipkart_url

HOSTS = ["www.flipkart.com", "flipkart.com", "dl.flipkart.com"]


def test_normalises_and_extracts_ids():
    v = validate_flipkart_url(
        "https://www.flipkart.com/some-phone-128gb/p/itmabc123def?pid=MOBABC123XYZ&lid=LST1&marketplace=FLIPKART", HOSTS
    )
    assert v.pid == "MOBABC123XYZ"
    assert v.item_id == "itmabc123def"
    assert v.canonical_url == "https://www.flipkart.com/some-phone-128gb/p/itmabc123def?pid=MOBABC123XYZ"
    assert v.is_product_page


def test_dl_links_are_mapped():
    v = validate_flipkart_url("https://dl.flipkart.com/dl/some-item/p/itmzzz999aaa?pid=ABCDEFGH1234", HOSTS)
    assert v.canonical_url.startswith("https://www.flipkart.com/some-item/p/itmzzz999aaa")


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example.com/p/itmabc123def",
        "https://www.flipkart.com.evil.com/p/itmabc123def",
        "https://user:pass@www.flipkart.com/p/itmabc123def",
        "https://127.0.0.1/p/itmabc123def",
        "https://www.flipkart.com:8443/p/itmabc123def",
        "ftp://www.flipkart.com/p/itmabc123def",
        "https://dl.flipkart.com/s/abcd",
        "",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(UrlValidationError):
        validate_flipkart_url(url, HOSTS)
