using SixLabors.ImageSharp;
using SixLabors.ImageSharp.Advanced;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;

namespace Vox2Pictoria;

public class PostProcessingService
{
    private static (int dx, int dy)[] _scanOffsets = [(0, -1), (0, 1), (-1, 0), (1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1),
        (0, -2), (0, 2), (-2, 0), (2, 0), (2, -1), (2, 1), (-2, -1), (-2, 1), (1, -2), (1, 2), (-1, -2), (-1, 2), (2, -2), (2, 2), (-2, -2), (-2, 2),
        (0, -3), (0, 3), (-3, 0), (3, 0), (3, -1), (3, 1), (-3, -1), (-3, 1), (1, -3), (1, 3), (-1, -3), (-1, 3), (3, -2), (3, 2), (-3, -2), (-3, 2), (2, -3), (2, 3), (-2, -3), (-2, 3), (3, -3), (3, 3), (-3, -3), (-3, 3),
        (0, -4), (0, 4), (-4, 0), (4, 0), (4, -1), (4, 1), (-4, -1), (-4, 1), (1, -4), (1, 4), (-1, -4), (-1, 4), (4, -2), (4, 2), (-4, -2), (-4, 2), (2, -4), (2, 4), (-2, -4), (-2, 4), (4, -3), (4, 3), (-4, -3), (-4, 3), (3, -4), (3, 4), (-3, -4), (-3, 4), (4, -4), (4, 4), (-4, -4), (-4, 4),
        (0, -5), (0, 5), (-5, 0), (5, 0), (5, -1), (5, 1), (-5, -1), (-5, 1), (1, -5), (1, 5), (-1, -5), (-1, 5), (5, -2), (5, 2), (-5, -2), (-5, 2), (2, -5), (2, 5), (-2, -5), (-2, 5), (5, -3), (5, 3), (-5, -3), (-5, 3), (3, -5), (3, 5), (-3, -5), (-3, 5), (5, -4), (5, 4), (-5, -4), (-5, 4), (4, -5), (4, 5), (-4, -5), (-4, 5), (5, -5), (5, 5), (-5, -5), (-5, 5),
        (0, -6), (0, 6), (-6, 0), (6, 0), (6, -1), (6, 1), (-6, -1), (-6, 1), (1, -6), (1, 6), (-1, -6), (-1, 6), (6, -2), (6, 2), (-6, -2), (-6, 2), (2, -6), (2, 6), (-2, -6), (-2, 6), (6, -3), (6, 3), (-6, -3), (-6, 3), (3, -6), (3, 6), (-3, -6), (-3, 6), (6, -4), (6, 4), (-6, -4), (-6, 4), (4, -6), (4, 6), (-4, -6), (-4, 6), (6, -5), (6, 5), (-6, -5), (-6, 5), (5, -6), (5, 6), (-5, -6), (-5, 6), (6, -6), (6, 6), (-6, -6), (-6, 6)];

    public static async Task CropAndScaleRenders(Dictionary<string, StructureInfo> structureNameStructureInfoMap, Options options)
    {
        // Create output directory if it doesn't already exist
        string binImagesPath = Path.Combine(options.BinDirectory, "images");
        if (!Directory.Exists(binImagesPath)) Directory.CreateDirectory(binImagesPath);

        // Clear files in output directory
        var files = Directory.GetFiles(binImagesPath);
        foreach (var file in files)
        {
            File.Delete(file);
        }

        // Crop, scale and save
        await Parallel.ForEachAsync(structureNameStructureInfoMap.Values, (structureInfo, CancellationToken) => CropScaleAndSaveStructureImage(structureInfo, options));
    }

    private static async ValueTask CropScaleAndSaveStructureImage(StructureInfo structureInfo, Options options)
    {
        try
        {
            // Get volume image offsets
            (int leftOffset, int topOffset, int cropWidth, int cropHeight) = await FindImageCropOffsetsAndDimensions(structureInfo, options);
            Console.WriteLine($"Structure: {structureInfo.Name}, Render offsets: Left: {leftOffset}, Top: {topOffset}, Width: {cropWidth}, Height: {cropHeight}");

            // Read actual image
            string actualImagePath = Path.Combine(options.RendersDirectory, $"{structureInfo.Name}.png");
            Image<Rgba32> actualImage = await Image.LoadAsync<Rgba32>(actualImagePath);

            // Crop actual image
            actualImage.Mutate(ctx => ctx.Crop(new Rectangle(leftOffset, topOffset, cropWidth, cropHeight)));

            // Fix occluded faces
            await FixOccludedFaces(actualImage, options, structureInfo, leftOffset, topOffset, cropWidth, cropHeight);

            // For debugging
            //
            // Save image with fixed occluded faces
            var savePath = Path.Combine(options.RendersDirectory, $"{structureInfo.Name}_fixed.png");
            await actualImage.SaveAsPngAsync(savePath);
            Console.WriteLine($"Fixed image saved at: {savePath}");

            // Scale actual image
            actualImage.Mutate(ctx => ctx.Resize(structureInfo.ImageDimensions.Width, structureInfo.ImageDimensions.Height));

            // Save final image
            var finalImageSavePath = Path.Combine(options.ImagesDirectory, $"{structureInfo.Name}.png");
            await actualImage.SaveAsPngAsync(finalImageSavePath);
            Console.WriteLine($"Final image saved at: {finalImageSavePath}");
        }
        catch (Exception error)
        {
            Console.WriteLine($"Error processing image for structure \"{structureInfo.Name}\": {error}");
            throw;
        }
    }

    private async static Task FixOccludedFaces(Image<Rgba32> actualImage, Options options, StructureInfo structureInfo, int leftOffset, int topOffset, int cropWidth, int cropHeight)
    {
        // Read occluded faces image
        string occludedFacesImagePath = Path.Combine(options.RendersDirectory, $"{structureInfo.Name}_occludedFaces.png");
        if (!File.Exists(occludedFacesImagePath)) return; // Some structures have no occluded faces
        Image<Rgba32> occludedFacesImage = await Image.LoadAsync<Rgba32>(occludedFacesImagePath);

        // Crop
        occludedFacesImage.Mutate(ctx => ctx.Crop(new Rectangle(leftOffset, topOffset, cropWidth, cropHeight)));

        // Iterate over occluded faces image pixels
        int minAlpha = 16;
        int width = actualImage.Width;
        int height = actualImage.Height;
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                byte a = occludedFacesImage.DangerousGetPixelRowMemory(y).Span[x].A;

                if (a < minAlpha)
                {
                    continue;
                }

                FixPixelColor(x, y, occludedFacesImage, actualImage, minAlpha);
            }
        }
    }

    // Scan pixels around current pixel in occluded image for first pixel with a < minAlpha. Scan concentric rings around pixel, starting with the innermost ring in the order top, bottom, left, right, top-right, bottom-right, 
    // bottom-left, top-left. Once a pixel is found, set the current pixel's color to that pixel's color.
    private static void FixPixelColor(int x, int y, Image<Rgba32> occludedFacesImage, Image<Rgba32> actualImage, int minAlpha)
    {
        Rgba32 actualImageRgba;
        for (int i = 0; i < _scanOffsets.Length; i++)
        {
            int newX = x + _scanOffsets[i].dx;
            int newY = y + _scanOffsets[i].dy;
            if (newX < 0 || newY < 0 || newX >= actualImage.Width || newY >= actualImage.Height)
            {
                continue;
            }

            // Occluded
            if (occludedFacesImage.DangerousGetPixelRowMemory(newY).Span[newX].A >= minAlpha)
            {
                continue;
            }

            // Get replacement
            actualImageRgba = actualImage.DangerousGetPixelRowMemory(newY).Span[newX];
            if (actualImageRgba.A == 0 || // Transparent (0, 0, 0) pixel, no point copying
                actualImageRgba.R < 16 && actualImageRgba.G < 16 && actualImageRgba.B < 16) // TODO this is a hack. We have situations where a narrow occluded area is adjacent to a not-occluded but hidden in a crevice area and the area we actually want to copy colors from. The 
                                                                                            // hidden area is above the occluded area, which means it is givern precedence. This hack copies from the area we want. A clean solution would find the edge closest to each occluded pixel,
                                                                                            // and find the pixel we want closest to the edge and use it, instead of the current system that gives precedence to top/right/bottom/left.
            {
                continue;
            }

            actualImageRgba.A = 255;
            actualImage[x, y] = actualImageRgba;
            return;
        }
    }

    private async static Task<(int leftOffset, int topOffset, int cropWidth, int cropHeight)> FindImageCropOffsetsAndDimensions(StructureInfo structureInfo, Options options)
    {
        string volumeImagePath = Path.Combine(options.TempDirectory, "renders", $"{structureInfo.Name}_volume.png");
        Image<Rgba32> volumeImage = await Image.LoadAsync<Rgba32>(volumeImagePath);

        // Have to manually toggle to get a good value. too much getting cropped > decrease. too much white space around > increase. Note that our shapes have fairly sharp, non-axis aligned points. This means
        // the pixels containing the points are not going to be opaque since only part of them will be covered by the shape. If we do higher res renders, we can increase this, the higher res we render,
        // the more accurate our crops will be
        int minAlpha = options.FullResolution ? 255 : 170;
        int width = volumeImage.Width;
        int height = volumeImage.Height;

        if (width == 0 || height == 0)
        {
            throw new InvalidOperationException("Invalid image metadata");
        }

        // Find offsets
        int topOffset = -1, bottomOffset = -1, leftOffset = -1, rightOffset = -1;
        for (int y = 0; y < height && topOffset == -1; y++)
        {
            for (int x = 0; x < width; x++)
            {
                byte a = volumeImage.DangerousGetPixelRowMemory(y).Span[x].A;

                if (a >= minAlpha)
                {
                    topOffset = y;
                    break;
                }
            }
        }
        for (int y = height - 1; y >= 0 && bottomOffset == -1; y--)
        {
            for (int x = 0; x < volumeImage.Width; x++)
            {
                byte a = volumeImage.DangerousGetPixelRowMemory(y).Span[x].A;

                if (a >= minAlpha)
                {
                    bottomOffset = y;
                    break;
                }
            }
        }
        for (int x = 0; x < width && leftOffset == -1; x++)
        {
            for (int y = 0; y < height; y++)
            {
                byte a = volumeImage.DangerousGetPixelRowMemory(y).Span[x].A;
                if (a >= minAlpha)
                {
                    leftOffset = x;
                    break;
                }
            }
        }

        for (int x = width - 1; x >= 0 && rightOffset == -1; x--)
        {
            for (int y = 0; y < height; y++)
            {
                byte a = volumeImage.DangerousGetPixelRowMemory(y).Span[x].A;
                if (a >= minAlpha)
                {
                    rightOffset = x;
                    break;
                }
            }
        }

        // Throw if any offset is -1
        if (leftOffset == -1 || rightOffset == -1 || topOffset == -1 || bottomOffset == -1)
        {
            throw new InvalidOperationException("Failed to calculate offsets. One or more offsets are -1.");
        }

        // Get width and height
        int candidateCropWidth = rightOffset - leftOffset + 1;
        int candidateCropHeight = bottomOffset - topOffset + 1;

        // Update height topOffset and candidateCropHeight to get closest aspect ratio to expectedAspectRatio as possible
        //
        // Also note that the isometric x length of structures is always an integer. Therefore, if we crop close to opaque pixels along the x-axis and adjust vertical height using expectedAspectRatio, we should 
        // get decently accurate crops.
        double expectedAspectRatio = (double)structureInfo.ImageDimensions.Width / structureInfo.ImageDimensions.Height;
        int adjustedHeight = (int)Math.Round(candidateCropWidth / expectedAspectRatio);
        int heightDiff = Math.Abs(adjustedHeight - candidateCropHeight);

        if (heightDiff > 0)
        {
            double topExcess = structureInfo.IsometricPolygon!.MinY - Math.Floor(structureInfo.IsometricPolygon.MinY);
            double bottomExcess = Math.Ceiling(structureInfo.IsometricPolygon.MaxY) - structureInfo.IsometricPolygon.MaxY;
            double totalExcess = topExcess + bottomExcess;

            if (adjustedHeight > candidateCropHeight)
            {
                topOffset -= (int)Math.Round(topExcess / totalExcess * heightDiff); // The larger top excess is, the larger a proportion of the heightDiff (empty pixels) we add to the top
            }
            else if (adjustedHeight < candidateCropHeight)
            {
                // Should not occur often
                topOffset += (int)Math.Round((1 - topExcess / totalExcess) * heightDiff); // The larger top excess is, the smaller a proportion of the heightDiff (pixels) we subtract from the top
            }
            candidateCropHeight = adjustedHeight;
        }

        // bottomOffset and rightOffset are indices from 0-based ranges that start from the top and left respectively. 
        return (leftOffset, topOffset, candidateCropWidth, candidateCropHeight);
    }
}