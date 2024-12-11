import bleach

# Test bleach functionality
clean_html = bleach.clean("<script>alert('XSS');</script><p>Hello World!</p>")
print(clean_html)  # Expected Output: <p>Hello World!</p>
