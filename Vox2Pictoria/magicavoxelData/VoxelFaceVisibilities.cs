using System.Runtime.InteropServices;

namespace Vox2Pictoria;

[StructLayout(LayoutKind.Sequential, Size = 6)]
public readonly struct CuboidFaceVisibilities(FaceVisibility minusXVisibility, FaceVisibility plusXVisibility, FaceVisibility minusYVisibility, FaceVisibility plusYVisibility, FaceVisibility minusZVisibility, FaceVisibility plusZVisibility)
{
    public readonly FaceVisibility MinusX = minusXVisibility;
    public readonly FaceVisibility PlusX = plusXVisibility;
    public readonly FaceVisibility MinusY = minusYVisibility;
    public readonly FaceVisibility PlusY = plusYVisibility;
    public readonly FaceVisibility MinusZ = minusZVisibility;
    public readonly FaceVisibility PlusZ = plusZVisibility;

    public readonly bool AnyVisible()
    {
        return MinusX != FaceVisibility.Hidden || PlusX != FaceVisibility.Hidden ||
               MinusY != FaceVisibility.Hidden || PlusY != FaceVisibility.Hidden ||
               MinusZ != FaceVisibility.Hidden || PlusZ != FaceVisibility.Hidden;
    }

    public readonly FaceVisibility GetFaceVisibility(Direction direction)
    {
        if (direction == Direction.MinusX) return MinusX;
        else if (direction == Direction.PlusX) return PlusX;
        else if (direction == Direction.MinusY) return MinusY;
        else if (direction == Direction.PlusY) return PlusY;
        else if (direction == Direction.MinusZ) return MinusZ;
        else if (direction == Direction.PlusZ) return PlusZ;
        else throw new ArgumentException("Invalid direction");
    }
}