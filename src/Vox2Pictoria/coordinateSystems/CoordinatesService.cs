namespace Vox2Pictoria;

public class CoordinatesService
{
    public static double CartesianXZToIsometricX(double x, double z)
    {
        return x - z;
    }

    public static double CartesianXYZToIsometricY(double x, double y, double z)
    {
        double root6 = Math.Sqrt(6);
        return (x + z - y * root6) / 2;
    }
}