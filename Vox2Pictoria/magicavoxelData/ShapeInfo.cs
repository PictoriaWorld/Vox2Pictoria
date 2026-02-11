using System.Text.Json.Serialization;
using FileToVoxCore.Schematics.Tools;
using FileToVoxCore.Utils;
using FileToVoxCore.Vox;
using FileToVoxCore.Vox.Chunks;

namespace Vox2Pictoria;

public class ShapeInfo(FrameInfo? frameInfo = null)
{
    public Cuboid PictoriaLocation = new(0, 0, 0, 0, 0, 0);
    private Cuboid _magicaVoxelLocation = new(int.MaxValue, int.MinValue, int.MaxValue, int.MinValue, int.MaxValue, int.MinValue);
    private FrameInfo? _frameInfo = frameInfo; // Note that ShapeInfos that exist only as parent shape infos do not have any associated frame, so this is null for them
    private readonly List<ShapeInfo> _childShapeInfos = [];
    private string? _parentTransformNodeName = null;
    private int _parentTransformNodeIndex = -1;

    [JsonPropertyName("location")]
    public Cuboid PictoriaLocationProperty
    {
        get => PictoriaLocation;
        private set => PictoriaLocation = value;
    }

    [JsonIgnore]
    public Cuboid MagicaVoxelLocation
    {
        get => _magicaVoxelLocation;
        private set => _magicaVoxelLocation = value;
    }

    [JsonIgnore]
    public FrameInfo? FrameInfo
    {
        get => _frameInfo;
        private set => _frameInfo = value;
    }

    [JsonIgnore]
    public string? ParentTransformNodeName
    {
        get => _parentTransformNodeName;
    }

    [JsonIgnore]
    public int ParentTransformNodeIndex
    {
        get => _parentTransformNodeIndex;
    }

    [JsonIgnore]
    public List<ShapeInfo> ChildShapeInfos
    {
        get => _childShapeInfos;
    }

    [JsonIgnore]
    public Matrix4x4Int TransformMatrix { get; private set; }

    [JsonIgnore]
    public Direction[] PostPreRotationDirectionsMap { get; } = new Direction[6];

    public void UpdatePostRotationFaceMap()
    {
        // Extract rotation from TransfomMatrixO
        Matrix4x4Int rotationMatrix = new(new Vector4Int(TransformMatrix.m00, TransformMatrix.m10, TransformMatrix.m20, 0),
            new Vector4Int(TransformMatrix.m01, TransformMatrix.m11, TransformMatrix.m21, 0),
            new Vector4Int(TransformMatrix.m02, TransformMatrix.m12, TransformMatrix.m22, 0),
            new Vector4Int(0, 0, 0, 1));

        // Rotate each face and determine the new face
        PostPreRotationDirectionsMap[(int)GetPostRotationFaceDirection(new Vector3Int(-1, 0, 0), ref rotationMatrix)] = Direction.MinusX;
        PostPreRotationDirectionsMap[(int)GetPostRotationFaceDirection(new Vector3Int(1, 0, 0), ref rotationMatrix)] = Direction.PlusX;
        PostPreRotationDirectionsMap[(int)GetPostRotationFaceDirection(new Vector3Int(0, -1, 0), ref rotationMatrix)] = Direction.MinusY;
        PostPreRotationDirectionsMap[(int)GetPostRotationFaceDirection(new Vector3Int(0, 1, 0), ref rotationMatrix)] = Direction.PlusY;
        PostPreRotationDirectionsMap[(int)GetPostRotationFaceDirection(new Vector3Int(0, 0, -1), ref rotationMatrix)] = Direction.MinusZ;
        PostPreRotationDirectionsMap[(int)GetPostRotationFaceDirection(new Vector3Int(0, 0, 1), ref rotationMatrix)] = Direction.PlusZ;
    }

    private static Direction GetPostRotationFaceDirection(Vector3Int face, ref Matrix4x4Int rotationMatrix)
    {
        Vector3Int rotatedFace = rotationMatrix.MultiplyVector(face);

        if (rotatedFace.X < 0) return Direction.MinusX;
        if (rotatedFace.X > 0) return Direction.PlusX;
        if (rotatedFace.Y < 0) return Direction.MinusY;
        if (rotatedFace.Y > 0) return Direction.PlusY;
        if (rotatedFace.Z < 0) return Direction.MinusZ;
        if (rotatedFace.Z > 0) return Direction.PlusZ;

        throw new InvalidOperationException("Face must correspond to a new face after rotation");
    }

    public void AddChildShapeInfo(ShapeInfo childShapeInfo)
    {
        _childShapeInfos.Add(childShapeInfo);

        int minX = _magicaVoxelLocation.MinX;
        int maxX = _magicaVoxelLocation.MaxX;
        int minY = _magicaVoxelLocation.MinY;
        int maxY = _magicaVoxelLocation.MaxY;
        int minZ = _magicaVoxelLocation.MinZ;
        int maxZ = _magicaVoxelLocation.MaxZ;

        Cuboid childLocation = childShapeInfo.MagicaVoxelLocation;
        minX = Math.Min(minX, childLocation.MinX);
        maxX = Math.Max(maxX, childLocation.MaxX);
        minY = Math.Min(minY, childLocation.MinY);
        maxY = Math.Max(maxY, childLocation.MaxY);
        minZ = Math.Min(minZ, childLocation.MinZ);
        maxZ = Math.Max(maxZ, childLocation.MaxZ);

        SetLocations(minX, maxX, minY, maxY, minZ, maxZ);
    }

    public void ApplyTransformationsToFrame(ref Matrix4x4Int transformMatrix)
    {
        SetTransformMatrix(ref transformMatrix, true);
    }

    public void ApplyTransformationsToFrame(TransformNodeChunk transformNodeChunk)
    {
        SetTransformMatrixFromTransformNodeChunk(transformNodeChunk, true);
    }

    public void ApplyTransformationsToExistingMagicaVoxelLocation(TransformNodeChunk transformNodeChunk)
    {
        SetTransformMatrixFromTransformNodeChunk(transformNodeChunk, false);
    }

    public void SetTransformMatrix(ref Matrix4x4Int matrix)
    {
        TransformMatrix = matrix;
        UpdatePostRotationFaceMap();
    }

    private void SetTransformMatrix(ref Matrix4x4Int matrix, bool applyToFrame)
    {
        TransformMatrix = matrix;
        UpdatePostRotationFaceMap();

        if (applyToFrame)
        {
            if (_frameInfo == null)
            {
                throw new InvalidOperationException("Cannot apply transform to shape that has no frame info");
            }
            SetLocations(0, _frameInfo.MagicaVoxelDimensions.X, 0, _frameInfo.MagicaVoxelDimensions.Y, 0, _frameInfo.MagicaVoxelDimensions.Z);
        }

        // Apply
        Vector3Int minPoint = new(MagicaVoxelLocation.MinX, MagicaVoxelLocation.MinY, MagicaVoxelLocation.MinZ);
        Vector3Int maxPoint = new(MagicaVoxelLocation.MaxX, MagicaVoxelLocation.MaxY, MagicaVoxelLocation.MaxZ); // If min is at 0, 0, 0 and lengths are 1, 1, 1, max is at 1, 1, 1
        minPoint = TransformMatrix.MultiplyPoint(minPoint);
        maxPoint = TransformMatrix.MultiplyPoint(maxPoint);
        int magicavoxelMinX = Math.Min(minPoint.X, maxPoint.X);
        int magicavoxelMaxX = Math.Max(minPoint.X, maxPoint.X);
        int magicavoxelMinY = Math.Min(minPoint.Y, maxPoint.Y);
        int magicavoxelMaxY = Math.Max(minPoint.Y, maxPoint.Y);
        int magicavoxelMinZ = Math.Min(minPoint.Z, maxPoint.Z);
        int magicavoxelMaxZ = Math.Max(minPoint.Z, maxPoint.Z);

        // Set locations
        SetLocations(magicavoxelMinX, magicavoxelMaxX, magicavoxelMinY, magicavoxelMaxY, magicavoxelMinZ, magicavoxelMaxZ);
    }

    private void SetTransformMatrixFromTransformNodeChunk(TransformNodeChunk transformNodeChunk, bool applyToFrame)
    {
        if (applyToFrame)
        {
            if (_frameInfo == null)
            {
                throw new InvalidOperationException("Cannot apply transform to shape that has no frame info");
            }
            SetLocations(0, _frameInfo.MagicaVoxelDimensions.X, 0, _frameInfo.MagicaVoxelDimensions.Y, 0, _frameInfo.MagicaVoxelDimensions.Z);
        }

        // Get transform matrix
        Vector3Int transformAttribute = new(transformNodeChunk.FrameAttributes[0]._t); // This is the translation from the origin to the center of the structure
        Rotation rotationAttribute = transformNodeChunk.FrameAttributes[0]._r;
        var translationToOriginMatrix = Matrix4x4Int.Translate(new Vector3Int(-MagicaVoxelLocation.MinX - MagicaVoxelLocation.XLength / 2,
            -MagicaVoxelLocation.MinY - MagicaVoxelLocation.YLength / 2,
            -MagicaVoxelLocation.MinZ - MagicaVoxelLocation.ZLength / 2));
        Matrix4x4Int rotationMatrix = new(VoxUtils.ReadMatrix4X4FromRotation(rotationAttribute, new Vector3(0, 0, 0)));
        var translationToLocationMatrix = Matrix4x4Int.Translate(new Vector3Int(transformAttribute.X, transformAttribute.Y, transformAttribute.Z));
        Matrix4x4Int transformMatrix = translationToLocationMatrix * rotationMatrix * translationToOriginMatrix;
        SetTransformMatrix(ref transformMatrix, applyToFrame);
    }

    public void SetLocations(int magicavoxelMinX, int magicavoxelMaxX, int magicavoxelMinY, int magicavoxelMaxY, int magicavoxelMinZ, int magicavoxelMaxZ)
    {
        _magicaVoxelLocation.Update(magicavoxelMinX, magicavoxelMaxX, magicavoxelMinY, magicavoxelMaxY, magicavoxelMinZ, magicavoxelMaxZ);

        // Note that magicavoxel x-axis = flipped pictoria z-axis, magicavoxel z-axis = pictoria y-axis, magicavoxel y-axis = flipped pictoria x-axis
        // Convert from magicavoxel to pictoria location
        int pictoriaMinX = -magicavoxelMaxY;
        int pictoriaMaxX = -magicavoxelMinY;
        int pictoriaMinY = magicavoxelMinZ;
        int pictoriaMaxY = magicavoxelMaxZ;
        int pictoriaMinZ = -magicavoxelMaxX;
        int pictoriaMaxZ = -magicavoxelMinX;

        PictoriaLocation.Update(pictoriaMinX, pictoriaMaxX, pictoriaMinY, pictoriaMaxY, pictoriaMinZ, pictoriaMaxZ);
    }

    public void SetParentTransformNodeNameAndIndex(string name, int index)
    {
        _parentTransformNodeName = name;
        _parentTransformNodeIndex = index;
    }
}