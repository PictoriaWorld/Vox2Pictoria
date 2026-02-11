namespace Vox2Pictoria;

public class IsometricPolygon
{
    public double MinX => _minX;
    public double MaxX => _maxX;
    public double MinY => _minY;
    public double MaxY => _maxY;
    private double _minX, _maxX, _minY, _maxY;

    private double[] _points;
    private int _pointsNumElements;

    public IsometricPolygon()
    {
        _points = new double[16]; // Initial capacity for 8 points (x and y for each)
        _pointsNumElements = 0;
        _minX = _minY = double.MaxValue;
        _maxX = _maxY = double.MinValue;
    }

    public void SetCuboid(Cuboid cuboidMinMax)
    {
        // Clear
        Array.Clear(_points, 0, _points.Length);
        _pointsNumElements = 0;
        _minX = _minY = double.MaxValue;
        _maxX = _maxY = double.MinValue;

        // Set
        int minX = cuboidMinMax.MinX;
        int maxX = cuboidMinMax.MaxX;
        int minY = cuboidMinMax.MinY;
        int maxY = cuboidMinMax.MaxY;
        int minZ = cuboidMinMax.MinZ;
        int maxZ = cuboidMinMax.MaxZ;

        if (minX == maxX) // Plane parallel to z-y plane
        {
            AddCartesianPoint(minX, minY, minZ);
            AddCartesianPoint(minX, minY, maxZ);
            AddCartesianPoint(minX, maxY, maxZ);
            AddCartesianPoint(minX, maxY, minZ);
        }
        else if (minY == maxY) // Plane parallel to x-z plane
        {
            AddCartesianPoint(minX, minY, minZ);
            AddCartesianPoint(maxX, minY, minZ);
            AddCartesianPoint(maxX, minY, maxZ);
            AddCartesianPoint(minX, minY, maxZ);
        }
        else if (minZ == maxZ) // Plane parallel to x-y plane
        {
            AddCartesianPoint(minX, minY, minZ);
            AddCartesianPoint(minX, maxY, minZ);
            AddCartesianPoint(maxX, maxY, minZ);
            AddCartesianPoint(maxX, minY, minZ);
        }
        else // Cuboid
        {
            AddCartesianPoint(minX, maxY, minZ); // p5
            AddCartesianPoint(maxX, maxY, minZ); // p6
            AddCartesianPoint(maxX, minY, minZ); // p2
            AddCartesianPoint(maxX, minY, maxZ); // p3
            AddCartesianPoint(minX, minY, maxZ); // p4
            AddCartesianPoint(minX, maxY, maxZ); // p8
        }
    }

    public void AddCartesianPoint(int x, int y, int z)
    {
        double isometricX = CoordinatesService.CartesianXZToIsometricX(x, z);
        double isometricY = CoordinatesService.CartesianXYZToIsometricY(x, y, z);

        if (_pointsNumElements == _points.Length)
        {
            Array.Resize(ref _points, _points.Length * 2);
        }

        _points[_pointsNumElements++] = isometricX;
        _points[_pointsNumElements++] = isometricY;

        _minX = Math.Min(_minX, isometricX);
        _maxX = Math.Max(_maxX, isometricX);
        _minY = Math.Min(_minY, isometricY);
        _maxY = Math.Max(_maxY, isometricY);
    }

    public int GetRoundedIsometricBoundingRectangleMinX()
    {
        return (int)Math.Floor(MinX);
    }

    public int GetRoundedIsometricBoundingRectangleMinY()
    {
        return (int)Math.Floor(MinY);
    }

    public int GetRoundedIsometricBoundingRectangleMaxX()
    {
        return (int)Math.Ceiling(MaxX);
    }

    public int GetRoundedIsometricBoundingRectangleMaxY()
    {
        return (int)Math.Ceiling(MaxY);
    }

    public int GetRoundedIsometricBoundingRectangleWidth()
    {
        return GetRoundedIsometricBoundingRectangleMaxX() - GetRoundedIsometricBoundingRectangleMinX();
    }

    public int GetRoundedIsometricBoundingRectangleHeight()
    {
        return GetRoundedIsometricBoundingRectangleMaxY() - GetRoundedIsometricBoundingRectangleMinY();
    }
}