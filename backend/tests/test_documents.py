import io

from tests.conftest import register_and_login


def test_upload_infers_type_from_extension(client):
    headers = register_and_login(client, "uploader@example.com")

    response = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("photo.jpg", io.BytesIO(b"not a real jpeg, just test bytes"), "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["original_file_name"] == "photo.jpg"
    assert body["document_type_name"] == "Image"
    assert body["file_size"] > 0


def test_upload_with_account_override_resolves_to_account_not_text(client):
    """
    The exact ambiguity this project had to fix: a plain `.json` upload is
    indistinguishable from a Text document by extension alone (both land in
    FileType.TEXT_EXTENSIONS). The frontend's "Analyze an account" form
    always sends document_type="Account" explicitly to disambiguate — see
    DocumentService.upload_document's docstring.
    """
    headers = register_and_login(client, "bot-analyst@example.com")

    response = client.post(
        "/api/documents/upload",
        headers=headers,
        data={"document_type": "Account"},
        files={"file": ("account_snapshot.json", io.BytesIO(b'{"screen_name": "x"}'), "application/json")},
    )

    assert response.status_code == 200
    assert response.json()["document_type_name"] == "Account"


def test_upload_json_without_override_resolves_to_text(client):
    """The other half of the same ambiguity: no override -> the FileType default."""
    headers = register_and_login(client, "text-uploader@example.com")

    response = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("article.json", io.BytesIO(b'{"headline": "..."}'), "application/json")},
    )

    assert response.status_code == 200
    assert response.json()["document_type_name"] == "Text"


def test_upload_rejects_an_unsupported_extension(client):
    headers = register_and_login(client, "bad-upload@example.com")

    response = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("archive.zip", io.BytesIO(b"PK\x03\x04"), "application/zip")},
    )

    assert response.status_code == 400


def test_upload_requires_authentication(client):
    response = client.post(
        "/api/documents/upload",
        files={"file": ("photo.jpg", io.BytesIO(b"data"), "image/jpeg")},
    )
    assert response.status_code == 401


def test_get_and_list_and_delete_document(client):
    headers = register_and_login(client, "lister@example.com")

    upload = client.post(
        "/api/documents/upload",
        headers=headers,
        files={"file": ("clip.mp4", io.BytesIO(b"fake video bytes"), "video/mp4")},
    )
    document_id = upload.json()["id"]

    fetched = client.get(f"/api/documents/{document_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["document_type_name"] == "Video"

    listed = client.get("/api/documents/", headers=headers)
    assert listed.status_code == 200
    assert any(doc["id"] == document_id for doc in listed.json())

    deleted = client.delete(f"/api/documents/{document_id}", headers=headers)
    assert deleted.status_code == 200

    missing = client.get(f"/api/documents/{document_id}", headers=headers)
    assert missing.status_code == 404


def test_get_missing_document_is_404(client):
    headers = register_and_login(client, "missing-doc@example.com")
    response = client.get("/api/documents/999999", headers=headers)
    assert response.status_code == 404
