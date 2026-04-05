"""Temperature converter utility for Fahrenheit, Celsius, and Kelvin."""


def f_to_c(temp):
    """Convert Fahrenheit to Celsius."""
    return (temp - 32) * 5 / 9


def c_to_f(temp):
    """Convert Celsius to Fahrenheit."""
    return temp * 9 / 5 + 32


def c_to_k(temp):
    """Convert Celsius to Kelvin."""
    return temp + 273.15


def k_to_c(temp):
    """Convert Kelvin to Celsius."""
    return temp - 273.15


if __name__ == "__main__":
    print("Temperature Conversions")
    print("-" * 30)

    f = 100
    print(f"{f}°F = {f_to_c(f):.2f}°C")

    c = 0
    print(f"{c}°C = {c_to_f(c):.2f}°F")

    c = 25
    print(f"{c}°C = {c_to_k(c):.2f}K")

    k = 300
    print(f"{k}K = {k_to_c(k):.2f}°C")
