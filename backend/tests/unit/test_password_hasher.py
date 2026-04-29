from app.core.security import PasswordHasher


def test_hash_and_verify() -> None:
    hasher = PasswordHasher()
    hashed = hasher.hash("hunter2")
    assert hashed != "hunter2"
    assert hasher.verify("hunter2", hashed) is True
    assert hasher.verify("wrong", hashed) is False
