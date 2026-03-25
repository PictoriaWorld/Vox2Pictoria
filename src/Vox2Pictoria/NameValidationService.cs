namespace Vox2Pictoria;

/// <summary>
/// Validates entity names using the same rules as Pictoria client and server:
/// required, ASCII alphanumeric only (A-Z, a-z, 0-9), max 32 characters.
/// </summary>
public static class NameValidationService
{
    /// <summary>
    /// Validates that a name is non-empty, ASCII alphanumeric only, and within max length.
    /// Returns null if valid, or an error message string if invalid.
    /// </summary>
    public static string? Validate(string name, string entityType)
    {
        if (string.IsNullOrWhiteSpace(name)) return $"{entityType} name is required (cannot be empty or whitespace).";

        if (name.Length > Constants.NameMaxLength) return $"{entityType} name '{name}' exceeds maximum length of {Constants.NameMaxLength} characters (has {name.Length}).";

        for (int i = 0; i < name.Length; i++)
        {
            char c = name[i];
            if (!(c >= 'A' && c <= 'Z') && !(c >= 'a' && c <= 'z') && !(c >= '0' && c <= '9'))
                return $"{entityType} name '{name}' contains invalid character '{c}' at position {i}. Only ASCII letters and digits are allowed.";
        }

        return null;
    }
}
