using FileToVoxCore.Schematics.Tools;

namespace Vox2Pictoria;

public struct GeneralObjInfo
{
    public Dictionary<Vector3, int> VertexListNumberMap = [];
    public List<QuadFace> QuadFaces = [];

    public GeneralObjInfo()
    {
    }
}