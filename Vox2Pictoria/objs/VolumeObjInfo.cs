using FileToVoxCore.Schematics.Tools;

namespace Vox2Pictoria;

public struct VolumeObjInfo
{
    public List<Vector3> VertexList = [];
    public List<TriFace> TriFaces = [];

    public VolumeObjInfo()
    {
    }
}