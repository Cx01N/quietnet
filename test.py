import psk


def test_send_receive(message):
    print(f"Original message: {message}")

    # Encode the message
    encoded_pattern = psk.encode(message)
    print(f"Encoded pattern: {encoded_pattern}")

    # Simulate transmission by converting the encoded pattern back to a list of bits
    transmitted_bits = [int(bit) for bit in encoded_pattern]
    print(f"Transmitted bits: {transmitted_bits}")

    # Decode the received bits
    try:
        decoded_message = psk.decode(transmitted_bits)
        print(f"Decoded message: {decoded_message}")
    except ValueError as e:
        print(f"Decoding error: {e}")


# Test the send/receive functionality
test_send_receive("test")
