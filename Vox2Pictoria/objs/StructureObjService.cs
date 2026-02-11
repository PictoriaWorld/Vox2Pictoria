using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Text;
using FileToVoxCore.Schematics.Tools;
using FileToVoxCore.Vox;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;

namespace Vox2Pictoria;

public class StructureObjService
{
    public static async Task GenerateStructureObjsAsync(Dictionary<string, StructureInfo> structureNameStructureInfoMap, ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
        Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap, VoxModel model, Options options)
    {
        Console.WriteLine("Generating structure objs...");

        // Generate texture and texture coords
        GenerateTextureAndPaletteNumberTextureCoordsMap(model, options.ObjOutputDirectory, out List<TextureCoords> textureCoords, out Dictionary<int, int> paletteNumberTextureCoordNumberMap);

        // Generate structure objs
        DateTime currentTime = DateTime.Now;
        await Parallel.ForEachAsync(structureNameStructureInfoMap.Values, (structureInfo, CancellationToken) => GenerateStructureObjAsync(structureInfo, model, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
            voxelFrameVisibleVoxelInfoMap, paletteNumberTextureCoordNumberMap, textureCoords, options.ObjOutputDirectory));
        Console.WriteLine($"Structure obj generation duration: {(DateTime.Now - currentTime).TotalSeconds} s");
    }

    private static async ValueTask GenerateStructureObjAsync(StructureInfo structureInfo, VoxModel model, ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
        Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap, Dictionary<int, int> paletteNumberTextureCoordNumberMap, List<TextureCoords> textureCoords, string outputDirectory)
    {
        GeneralObjInfo objInfo = new();

        // Create obj info
        if (structureInfo.ShapeInfo.ChildShapeInfos.Count == 0)
        {
            AddVerticesAndFacesForShape(structureInfo.ShapeInfo, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, voxelFrameVisibleVoxelInfoMap, paletteNumberTextureCoordNumberMap, null, ref objInfo);
        }
        else
        {
            object objInfoLock = new();
            Parallel.ForEach(structureInfo.ShapeInfo.ChildShapeInfos, childShapeInfo => AddVerticesAndFacesForShape(childShapeInfo, transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
                voxelFrameVisibleVoxelInfoMap, paletteNumberTextureCoordNumberMap, objInfoLock, ref objInfo));
        }

        // Generate obj content
        StringBuilder stringBuilder = new();
        GenerateObjContent(stringBuilder, textureCoords, ref objInfo);

        // Write obj file
        //
        // <outputDirectory>/<structureInfo.Name>.obj
        string objPath = Path.Combine(outputDirectory, structureInfo.Name + ".obj");
        await File.WriteAllTextAsync(objPath, stringBuilder.ToString());
        Console.WriteLine($"Obj generated for structure '{structureInfo.Name}' at path: {objPath}");
    }

    [MethodImpl(MethodImplOptions.AggressiveInlining)]
    private static void AddVerticesAndFacesForShape(ShapeInfo shapeInfo, ConcurrentDictionary<Vector3Int, CuboidFaceVisibilities> transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap,
        Dictionary<int, Dictionary<int, VisibleVoxelInfo>> voxelFrameVisibleVoxelInfoMap, Dictionary<int, int> paletteNumberTextureCoordNumberMap, object? objInfoLock, ref GeneralObjInfo target)
    {
        FrameInfo? frameInfo = shapeInfo.FrameInfo;
        if (frameInfo == null || frameInfo.VoxelFrameIndex < 0)
        {
            throw new InvalidOperationException("FrameInfo should not be null and VoxelFrameIndex of FrameInfo belonging to structure with only one shape must not be less than 0");
        }
        Dictionary<int, VisibleVoxelInfo> voxelIndexVisibleVoxelInfoMap = voxelFrameVisibleVoxelInfoMap[frameInfo.VoxelFrameIndex];
        Matrix4x4Int transformMatrix = shapeInfo.TransformMatrix;

        // Generate vertices and faces
        // Iterate through the voxel data
        float objMinX, objMinY, objMinZ, objMaxX, objMaxY, objMaxZ;
        Vector3 voxelVertices0, voxelVertices1, voxelVertices2, voxelVertices3, voxelVertices4, voxelVertices5, voxelVertices6, voxelVertices7;
        int neighbourTransformedMinZ;
        foreach (KeyValuePair<int, VisibleVoxelInfo> voxelIndexVisibleVoxelInfo in voxelIndexVisibleVoxelInfoMap)
        {
            int index = voxelIndexVisibleVoxelInfo.Key;

            // Get transformed voxel bounding box
            //
            // Note that minX, minY and minZ correspond to voxel coordinate x, y and z respectively
            Cuboid untransformedVoxelBoundingBox = voxelIndexVisibleVoxelInfo.Value.UntransformedVoxelBoundingBox;
            Cuboid transformedVoxelBoundingBox = VoxelCoordinatesService.UntransformedToTransformedBoundingBox(ref untransformedVoxelBoundingBox, ref transformMatrix);

            // Convert transformed voxel bounding box coordinates to obj coordinates
            objMinX = (float)Math.Round(transformedVoxelBoundingBox.MinX / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMinY = (float)Math.Round(transformedVoxelBoundingBox.MinY / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMinZ = (float)Math.Round(transformedVoxelBoundingBox.MinZ / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMaxX = (float)Math.Round(transformedVoxelBoundingBox.MaxX / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMaxY = (float)Math.Round(transformedVoxelBoundingBox.MaxY / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);
            objMaxZ = (float)Math.Round(transformedVoxelBoundingBox.MaxZ / Constants.PictoriaCartesianToBlenderWorldDivisor, 1);

            // Get vertices
            //
            // Note that they are ordered like so: starts from the vertex at min obj x, y and z, then goes around the lower square (// to the x-y plane), then moves to the min obj x and y at max z and goes around the upper square.
            voxelVertices0 = new Vector3 { X = objMinX, Y = objMinY, Z = objMinZ };
            voxelVertices1 = new Vector3 { X = objMaxX, Y = objMinY, Z = objMinZ };
            voxelVertices2 = new Vector3 { X = objMaxX, Y = objMaxY, Z = objMinZ };
            voxelVertices3 = new Vector3 { X = objMinX, Y = objMaxY, Z = objMinZ };
            voxelVertices4 = new Vector3 { X = objMinX, Y = objMinY, Z = objMaxZ };
            voxelVertices5 = new Vector3 { X = objMaxX, Y = objMinY, Z = objMaxZ };
            voxelVertices6 = new Vector3 { X = objMaxX, Y = objMaxY, Z = objMaxZ };
            voxelVertices7 = new Vector3 { X = objMinX, Y = objMaxY, Z = objMaxZ };

            // Get frame face visibility
            //
            // This is the visibility of the face before considering other shapes (frames) and structures
            CuboidFaceVisibilities transformedFaceVisibility = transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap[new Vector3Int(transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MinY,
                transformedVoxelBoundingBox.MinZ)]; // Should not throw

            // Add vertices and faces
            //
            // Note that if within the frame, we've already ascertained that the voxel is obscurred in a direction, we can skip it. Also, if voxel is not at edge of frame, we do not need to check whether 
            // it is obscured by an adjacent shape.
            int texCoordsNumber = paletteNumberTextureCoordNumberMap[voxelIndexVisibleVoxelInfo.Value.PaletteNumber];
            if (transformedFaceVisibility.MinusX == FaceVisibility.Visible ||
                transformedFaceVisibility.MinusX == FaceVisibility.VisibleAtFrameEdge &&
                !SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX - 1, transformedVoxelBoundingBox.MinY, transformedVoxelBoundingBox.MinZ)) // -x face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices0, ref voxelVertices4, ref voxelVertices7, ref voxelVertices3, texCoordsNumber, 1, objInfoLock);
            }
            if (transformedFaceVisibility.PlusX == FaceVisibility.Visible ||
                transformedFaceVisibility.PlusX == FaceVisibility.VisibleAtFrameEdge &&
                !SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MaxX, transformedVoxelBoundingBox.MinY, transformedVoxelBoundingBox.MinZ)) // +x face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices5, ref voxelVertices1, ref voxelVertices2, ref voxelVertices6, texCoordsNumber, 2, objInfoLock);
            }
            if (transformedFaceVisibility.MinusY == FaceVisibility.Visible ||
                transformedFaceVisibility.MinusY == FaceVisibility.VisibleAtFrameEdge &&
                !SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MinY - 1, transformedVoxelBoundingBox.MinZ)) // -y face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices0, ref voxelVertices1, ref voxelVertices5, ref voxelVertices4, texCoordsNumber, 3, objInfoLock);
            }
            if (transformedFaceVisibility.PlusY == FaceVisibility.Visible ||
                transformedFaceVisibility.PlusY == FaceVisibility.VisibleAtFrameEdge &&
                !SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MaxY, transformedVoxelBoundingBox.MinZ)) // +y face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices3, ref voxelVertices7, ref voxelVertices6, ref voxelVertices2, texCoordsNumber, 4, objInfoLock);
            }
            if (transformedFaceVisibility.MinusZ == FaceVisibility.Visible ||
                transformedFaceVisibility.MinusZ == FaceVisibility.VisibleAtFrameEdge &&
                (neighbourTransformedMinZ = transformedVoxelBoundingBox.MinZ - 1) >= 0 && // Hide ground faces
                !SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MinY, neighbourTransformedMinZ)) // -z face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices0, ref voxelVertices3, ref voxelVertices2, ref voxelVertices1, texCoordsNumber, 5, objInfoLock);
            }
            if (transformedFaceVisibility.PlusZ == FaceVisibility.Visible ||
                transformedFaceVisibility.PlusZ == FaceVisibility.VisibleAtFrameEdge &&
                !SharedObjService.CheckIfFaceObscuredByAdjacentShape(transformedVisibleVoxelMinCoordinatesFrameFaceVisibilityMap, transformedVoxelBoundingBox.MinX, transformedVoxelBoundingBox.MinY, transformedVoxelBoundingBox.MaxZ)) // +z face
            {
                SharedObjService.AddVerticesAndFacesForDirection(ref target, ref voxelVertices4, ref voxelVertices5, ref voxelVertices6, ref voxelVertices7, texCoordsNumber, 6, objInfoLock);
            }
        }
    }

    private static void GenerateObjContent(StringBuilder stringBuilder, List<TextureCoords> textureCoords, ref GeneralObjInfo objInfo)
    {
        // Material
        stringBuilder.AppendLine("# material");
        stringBuilder.AppendLine("mtllib structures.mtl");
        stringBuilder.AppendLine("usemtl palette");

        // Normals
        stringBuilder.AppendLine("\n# normals\nvn -1 0 0\nvn 1 0 0\nvn 0 0 1\nvn 0 0 -1\nvn 0 -1 0\nvn 0 1 0");

        // Texcoords
        stringBuilder.AppendLine("\n# texcoords");
        foreach (TextureCoords texCoord in textureCoords)
        {
            stringBuilder.Append("vt ");
            stringBuilder.Append(texCoord.UCoordinate);
            stringBuilder.Append(' ');
            stringBuilder.Append(texCoord.VCoordinate);
            stringBuilder.AppendLine();
        }

        // Vertices
        stringBuilder.AppendLine("\n# vertices");
        foreach (Vector3 vertex in objInfo.VertexListNumberMap.Keys)
        {
            // Blender swaps and negates some axes when it imports objs (https://projects.blender.org/blender/blender/issues/31693). We need to compensate for that here.
            stringBuilder.Append("v ");
            stringBuilder.Append(vertex.X);
            stringBuilder.Append(' ');
            stringBuilder.Append(vertex.Z);
            stringBuilder.Append(' ');
            stringBuilder.Append(-vertex.Y);
            stringBuilder.AppendLine();
        }

        // Faces
        stringBuilder.AppendLine("\n# faces");
        foreach (QuadFace face in objInfo.QuadFaces)
        {
            // Triangle 1
            stringBuilder.Append("f ");
            stringBuilder.Append(face.VertexIndex1);
            stringBuilder.Append('/');
            stringBuilder.Append(face.TextureCoordsNumber);
            stringBuilder.Append('/');
            stringBuilder.Append(face.NormalNumber);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex2);
            stringBuilder.Append('/');
            stringBuilder.Append(face.TextureCoordsNumber);
            stringBuilder.Append('/');
            stringBuilder.Append(face.NormalNumber);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex3);
            stringBuilder.Append('/');
            stringBuilder.Append(face.TextureCoordsNumber);
            stringBuilder.Append('/');
            stringBuilder.Append(face.NormalNumber);
            stringBuilder.AppendLine();

            // Triangle 2
            stringBuilder.Append("f ");
            stringBuilder.Append(face.VertexIndex1);
            stringBuilder.Append('/');
            stringBuilder.Append(face.TextureCoordsNumber);
            stringBuilder.Append('/');
            stringBuilder.Append(face.NormalNumber);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex3);
            stringBuilder.Append('/');
            stringBuilder.Append(face.TextureCoordsNumber);
            stringBuilder.Append('/');
            stringBuilder.Append(face.NormalNumber);
            stringBuilder.Append(' ');
            stringBuilder.Append(face.VertexIndex4);
            stringBuilder.Append('/');
            stringBuilder.Append(face.TextureCoordsNumber);
            stringBuilder.Append('/');
            stringBuilder.Append(face.NormalNumber);
            stringBuilder.AppendLine();
        }
    }

    private static void GenerateTextureAndPaletteNumberTextureCoordsMap(VoxModel model, string outputDirectory, out List<TextureCoords> textureCoords, out Dictionary<int, int> paletteNumberTextureCoordNumberMap)
    {
        textureCoords = [];
        paletteNumberTextureCoordNumberMap = [];
        int numColors = model.ColorUsed.Count;

        using (Image<Rgba32> texture = new(numColors, 1))
        {
            int textureIndex = 0;
            foreach (int paletteNumber in model.ColorUsed)
            {
                FileToVoxCore.Drawing.Color color = model.Palette[paletteNumber - 1];
                texture[textureIndex, 0] = new Rgba32(color.R, color.G, color.B, 255);

                TextureCoords textureCoord = new((textureIndex + 0.5) / numColors, 0.5);
                paletteNumberTextureCoordNumberMap[paletteNumber] = textureCoords.Count + 1;
                textureCoords.Add(textureCoord);

                textureIndex++;
            }
            texture.SaveAsPng(Path.Combine(outputDirectory, "texture.png"));
        }
        Console.WriteLine("Texture and palette number - TextureCoords map generated");
    }
}