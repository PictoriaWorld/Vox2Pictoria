using StaticMock;
using Xunit;

namespace Vox2Pictoria.Tests;

public class DefinitionServiceIntegrationTests
{
    private static readonly string _assetsPath = Path.GetFullPath(Path.Combine(Directory.GetCurrentDirectory(), "DefinitionServiceIntegrationTestsAssets"));

    [Fact]
    public async Task GeneratePstrFiles_WithDummyStructure_GeneratesExpectedArchive()
    {
        // Arrange
        var dummyOptions = new Options(["dummyStructure1.vox", "-o", _assetsPath]);
        Dictionary<string, StructureInfo> dummyStructure1Map = CreateDummyStructureMap();
        using var mock = Mock.Setup(() => DateTimeOffset.UtcNow).Returns(new DateTimeOffset(2025, 1, 1, 0, 0, 0, TimeSpan.Zero));

        // Act
        await DefinitionService.GeneratePstrFiles(dummyStructure1Map, dummyOptions);

        // Assert
        AssertFileMatchesExpected(
            Path.Combine(_assetsPath, "bin/StructureDefinitions/dummyStructure1.pstr"),
            Path.Combine(_assetsPath, "dummyStructure1.pstr"));
        AssertFileMatchesExpected(
            Path.Combine(_assetsPath, "bin/StructureDefinitions/dummyStructure2.pstr"),
            Path.Combine(_assetsPath, "dummyStructure2.pstr"));
    }

    [Fact]
    public async Task GeneratePptyFile_WithDummyStructure_GeneratesExpectedArchive()
    {
        // Arrange
        var dummyOptions = new Options(["dummyProperty.vox", "-o", _assetsPath]);
        Dictionary<string, StructureInfo> dummyStructure1Map = CreateDummyStructureMap();

        // Act
        using var mock = Mock.Setup(() => DateTimeOffset.UtcNow).Returns(new DateTimeOffset(2025, 1, 1, 0, 0, 0, TimeSpan.Zero));
        await DefinitionService.GeneratePptyFile(dummyStructure1Map, dummyOptions);

        // Assert
        string actualPath = Path.Combine(_assetsPath, "bin/PropertyDefinition/dummyProperty.ppty");
        string expectedPath = Path.Combine(_assetsPath, "dummyProperty.ppty");
        AssertFileMatchesExpected(actualPath, expectedPath);
    }

    private static Dictionary<string, StructureInfo> CreateDummyStructureMap()
    {
        var dummyShapeInfo1 = new ShapeInfo();
        dummyShapeInfo1.SetLocations(-48, 48, -32, 32, -64, 64);
        var dummyStructure1Info1 = new StructureInfo(dummyShapeInfo1, "dummyStructure1", VolumeType.Cuboid);

        var dummyShapeInfo2 = new ShapeInfo();
        dummyShapeInfo2.SetLocations(56, 88, -16, 16, -32, 32);
        var dummyStructure1Info2 = new StructureInfo(dummyShapeInfo2, "dummyStructure2", VolumeType.Cuboid);

        return new Dictionary<string, StructureInfo>
        {
            ["dummyStructure1"] = dummyStructure1Info1,
            ["dummyStructure2"] = dummyStructure1Info2,
        };
    }

    private static void AssertFileMatchesExpected(string actualPath, string expectedPath)
    {
        byte[] actualBytes = File.ReadAllBytes(actualPath);

        // First run: save actual as expected for manual inspection, then fail
        if (!File.Exists(expectedPath))
        {
            File.WriteAllBytes(expectedPath, actualBytes);
            Assert.Fail($"Expected file did not exist. Saved to {expectedPath} ({actualBytes.Length} bytes) — inspect manually then re-run.");
        }

        // Subsequent runs: byte-for-byte comparison
        byte[] expectedBytes = File.ReadAllBytes(expectedPath);
        Assert.Equal(expectedBytes.Length, actualBytes.Length);
        Assert.Equal(expectedBytes, actualBytes);
    }
}
