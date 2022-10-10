import sys, os, time, shutil, mozjpeg_lossless_optimization, statistics
from subprocess import DEVNULL, STDOUT, check_call
from datetime import datetime
from shutil import rmtree, move
from pathlib import Path
from io import BytesIO
from PIL import Image
from DifPy import dif

# Declarations ---------------------------------------------------
IMAGES = []
watch_start = datetime.now()
RUNNING_DIR = str(Path(__file__).parent.resolve())
# Declarations ---------------------------------------------------

# Settings -------------------------------------------------------
DEBUG = True # whether you should see more info than you would normally need
BASE_DIR = Path(RUNNING_DIR + '/Images/Base') # dir where images are located
EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'] # allowed image extensions for processing
FORCE_CREATE_DIRS = True # we dont ask user if they want directories created
DELETE_DIRS_AFTER_FINISH = True # deletes temporary directories (OPTIMALIZED_IMGS_DIR_BASE, UPSCALED_IMGS_DIR, DUPLICATES_DIR if it's empty)

# Image duplicity handling
ALLOW_DELETING = True # will ask if you want to delete duplicates
ALLOW_DUPLICATES = True # will ask if you want to copy duplicates (only variations, not 1:1) to DUPLICATES_DIR for manual sorting
Image.MAX_IMAGE_PIXELS = 1000000000 # max size of image in pixels (set low only in case that you process some random uploads as it's to prevent decompression bomb DOS attack)
IMAGE_SIMILIARITY = "low" # low, normal, high or any int, which will be used as MSE threshold for comparison
DUPLICATES_DIR = Path(RUNNING_DIR + '/Images/Duplicates') # dir where duplicates will be stored for manual sorting

# Image optimalitazion
OPTIMALIZED_IMGS_DIR_BASE = Path(RUNNING_DIR + '/Images/OptimalizedBase') # dir where base optimalized images should be stored
OPTIMALIZED_IMGS_DIR_UPSCALED = Path(RUNNING_DIR + '/Images/BaseUpscaledOptimalized') # dir where base optimalized images should be stored
OPTIMALIZATION_QUALITY = 70 # sets quality of image (worst, lower size 0 - 100 best, bigger size)

# Image upscaling
REALSRGAN_PATH = Path(RUNNING_DIR + '/Real-ESRGAN/realesrgan-ncnn-vulkan.exe') # path to executable that will do the upscaling
UPSCALED_IMGS_DIR = Path(RUNNING_DIR + '/Images/Upscaled') # dir where upscaled images will be stored
UPSCALING_MODEL = "realesrgan-x4plus-anime" # model to be used when upscaling
UPSCALE_SIZE = 4 # upscaled image will be X times the size of original
UPSCALE_USE_GPU_ID = 0 # id of GPU to be used
UPSCALE_OUTPUT_FORMAT = "jpg" # output format of uspcaled image
UPSCALE_CMD_TEMPLATE = '"{}" -i "{}" -o "{}" -n {} -s {} -g {} -f {}' # template command with params for the upscaller
UPSCALE_SKIP_MIN_MIL_PIXELS = 10 # how many milions of pixels muset be in image so that we skip it's upscaling, try to experiment with this value to see what's best for your image set (low - faster upscaling, high - best quality)
# Settings -------------------------------------------------------

def clear():
    os.system('cls')

def logo():
    print("  _   _            ____        ")
    print(" | | | | ___ _ __ |  _ \ _   _ ")
    print(" | |_| |/ _ \ '_ \| |_) | | | |")
    print(" |  _  |  __/ | | |  __/| |_| |")
    print(" |_| |_|\___|_| |_|_|    \__, |")
    print("                         |___/ ")
    print("                               ")
    print("Made with  <3  by  Safiron#8888")

def debug(msg):
    if DEBUG:
        print(msg)

def start_watch():
    global watch_start
    watch_start = datetime.now()

def end_watch(action):
    print("{} took {} seconds".format(action, round((datetime.now()-watch_start).total_seconds(), 2)))

def askYN(message):
    while True:
        response = input("{} (y/n): ".format(message))

        if response == "y":
            return True

        if response == "n":
            return False

def check_directory(DIR, DIR_NAME, ERR_IF_NOT_EXISTS):
    if DIR.exists():
        if not DIR.is_dir():
            sys.exit("{}: {} is not directory".format(DIR_NAME, DIR))
        else:
            debug("{}: {}".format(DIR_NAME, DIR))
    else:
        if ERR_IF_NOT_EXISTS:
            sys.exit("{}: {} does not exists. Stopping execution.".format(DIR_NAME, DIR))
        else:
            if FORCE_CREATE_DIRS:
                os.makedirs(DIR)
                debug("{}: {}".format(DIR_NAME, DIR))
            else:
                if askYN("{}: {} does not exists. Do you want to create it?".format(DIR_NAME, DIR)):
                    os.makedirs(DIR)
                else:
                    sys.exit("Stopping execution as directory is needed.")

def init():
    debug("0.1 Check directories")

    check_directory(BASE_DIR, "BASE_DIR", True)
    check_directory(OPTIMALIZED_IMGS_DIR_BASE, "OPTIMALIZED_IMGS_DIR_BASE", False)
    check_directory(OPTIMALIZED_IMGS_DIR_UPSCALED, "OPTIMALIZED_IMGS_DIR_UPSCALED", False)

    if ALLOW_DUPLICATES:
        check_directory(DUPLICATES_DIR, "DUPLICATES_DIR", False)

    check_directory(UPSCALED_IMGS_DIR, "UPSCALED_IMGS_DIR", False)

    debug("REALSRGAN_PATH: {}".format(REALSRGAN_PATH))

    if not REALSRGAN_PATH.exists():
        sys.exit("REALSRGAN was not found on this path.")

    debug("\n0.2 Check settings")
    debug("EXTENSIONS: {}".format(EXTENSIONS))
    debug("FORCE_CREATE_DIRS: {}".format(FORCE_CREATE_DIRS))
    debug("DELETE_DIRS_AFTER_FINISH: {}".format(DELETE_DIRS_AFTER_FINISH))
    debug("ALLOW_DELETING: {}".format(ALLOW_DELETING))
    debug("ALLOW_DUPLICATES: {}".format(ALLOW_DUPLICATES))
    debug("IMAGE_SIMILIARITY: {}".format(IMAGE_SIMILIARITY))
    debug("OPTIMALIZATION_QUALITY: {}".format(OPTIMALIZATION_QUALITY))
    debug("UPSCALING_MODEL: {}".format(UPSCALING_MODEL))
    debug("UPSCALE_SIZE: {}".format(UPSCALE_SIZE))
    debug("UPSCALE_USE_GPU_ID: {}".format(UPSCALE_USE_GPU_ID))
    debug("UPSCALE_OUTPUT_FORMAT: {}".format(UPSCALE_OUTPUT_FORMAT))
    debug("UPSCALE_SKIP_MIN_MIL_PIXELS: {}".format(UPSCALE_SKIP_MIN_MIL_PIXELS))

def index_images(DIR):
    global IMAGES
    IMAGES = []

    print("Indexing [{}] images in {}".format('|'.join(EXTENSIONS), str(DIR)))
    start_watch()

    for path in DIR.glob(r'**/*'):
        if path.exists():
            if path.suffix.lower() in EXTENSIONS:
                if path.is_file():
                    IMAGES.append(path)

    print("Indexed {} images".format(len(IMAGES)))
    end_watch("Indexing")

def find_duplicate_images(DIR):
    print("Looking for duplicates in {}".format(DIR))

    search = dif(DIR, similarity=IMAGE_SIMILIARITY)

    if len(search.lower_quality) > 0:
        COPY_DUPLICATES = False

        if ALLOW_DUPLICATES:
            if askYN("Save original vs duplicates to {} ?".format(DUPLICATES_DIR)):
                COPY_DUPLICATES = True

        print("List of duplicate/similar images (original -> duplicates):\n")

        for result in search.result:
            duplicity_result = search.result[result]

            print("{} {}".format(result, duplicity_result["filename"]))

            if COPY_DUPLICATES:
                shutil.copy(duplicity_result["location"], DUPLICATES_DIR.joinpath("{} original{}".format(result, Path(duplicity_result["location"]).suffix)))

            for i in range(0, len(duplicity_result["duplicates"]["paths"])):
                duplicit_image = duplicity_result["duplicates"]["paths"][i]
                diff = duplicity_result["duplicates"]["diffs"][i]

                print("\t{} {} [{}]".format(result, Path(duplicit_image).name, diff))

                if COPY_DUPLICATES and int(float(diff)) > 0:
                    shutil.copy(duplicit_image, DUPLICATES_DIR.joinpath("{} duplicity variation {}{}".format(result, i, Path(duplicity_result["location"]).suffix)))

        if ALLOW_DELETING:
            if askYN("\nDelete duplicates?".format(DUPLICATES_DIR)):
                delete_images(search.lower_quality)

def delete_images(images):
    print("")

    deleted = 0

    for file in images:
        file_path = Path(file)

        try:
            os.remove(file_path)
            deleted += 1

            print("Deleted {}".format(file_path.name))
        except:
            print("Could not delete image {}".format(file_path))

    print("Deleted {} images".format(deleted))

def convert_to_optimized_jpeg(input_path, output_path):
    jpeg_io = BytesIO()

    with Image.open(input_path, "r") as image:
        image.convert("RGB").save(jpeg_io, format="JPEG", quality=OPTIMALIZATION_QUALITY)

    jpeg_io.seek(0)
    jpeg_bytes = jpeg_io.read()

    optimized_jpeg_bytes = mozjpeg_lossless_optimization.optimize(jpeg_bytes)

    with open(output_path, "wb") as output_file:
        output_file.write(optimized_jpeg_bytes)

def optimalize_images(DIR):
    print("Optimalizing images to jpg with {}% quality and saving them to {}".format(OPTIMALIZATION_QUALITY, DIR))
    start_watch()

    images_len = len(IMAGES)

    for i in range(0, images_len):
        image = IMAGES[i]

        print("Optimalizing images: [{}/{}] [{}%]".format(i+1, images_len, round(((i+1)/images_len * 100))), end="\r")

        new_path = Path(DIR.joinpath(image.stem + ".jpg"))

        if not new_path.exists():
            convert_to_optimized_jpeg(image, new_path)

    print("Optimalizing images: [{}/{}] [100%]".format(images_len, images_len))
    end_watch("Optimalizing")

def upscale_images(INPUT_DIR, OUTPUT_DIR):
    debug("Determining which images have enough quality to not be upscaled")

    already_upscaled_imgs = []
    upscale_skipped_imgs = []

    pixels_needed_to_skip = (UPSCALE_SKIP_MIN_MIL_PIXELS * 1000000)

    for img in IMAGES:
        with Image.open(img) as image:
            width, height = image.size
            total_pixels = (width * height)

            if OPTIMALIZED_IMGS_DIR_UPSCALED.joinpath(img.name).exists():
                already_upscaled_imgs.append(img)
                debug("{} will be skipped as it's already present in upscaled images".format(img.name))
            elif total_pixels > pixels_needed_to_skip:
                upscale_skipped_imgs.append(img)
                debug("{} will be skipped as it has {} pixels ({}x{})".format(img.name, total_pixels, width, height))

    for image in already_upscaled_imgs:
        os.remove(image)
        IMAGES.remove(image)

    if len(already_upscaled_imgs) > 0:
        print("Skipping {} image(s) that are already present in upscaled images {}".format(len(already_upscaled_imgs), OPTIMALIZED_IMGS_DIR_UPSCALED))

    for image in upscale_skipped_imgs:
        move(image, OPTIMALIZED_IMGS_DIR_UPSCALED.joinpath(image.name))
        IMAGES.remove(image)

    if len(upscale_skipped_imgs) > 0:
        print("{} image(s) are of high quality to not be upscaled, they will be moved to {}".format(len(upscale_skipped_imgs), OPTIMALIZED_IMGS_DIR_UPSCALED))
    
    if len(IMAGES) > 0:
        upscaling_cmd = UPSCALE_CMD_TEMPLATE.format(REALSRGAN_PATH, INPUT_DIR, OUTPUT_DIR, UPSCALING_MODEL, UPSCALE_SIZE, UPSCALE_USE_GPU_ID, UPSCALE_OUTPUT_FORMAT)

        debug("Calling upscaller using:")
        debug(upscaling_cmd + "\n")
        print("Upscalling {} image(s), you can check progress by looking in {}".format(len(IMAGES), UPSCALED_IMGS_DIR))

        start_watch()
        check_call(upscaling_cmd, stdout=DEVNULL, stderr=STDOUT)
        end_watch("Upscalling")
    else:
        print("No images left to upscale")

def is_dir_empty(DIR):
    try:
        with os.scandir(DIR) as it:
            return not any(it)
    except FileNotFoundError:
        return False

def cleanup():
    if DELETE_DIRS_AFTER_FINISH:
        print("\n8. Cleanup\n") # if there are more steps, the number should change

        print("Deleting temporary directory {}".format(OPTIMALIZED_IMGS_DIR_BASE))
        rmtree(OPTIMALIZED_IMGS_DIR_BASE)

        print("Deleting temporary directory {}".format(UPSCALED_IMGS_DIR))
        rmtree(UPSCALED_IMGS_DIR)

        if is_dir_empty(DUPLICATES_DIR):
            print("Deleting directory with duplicates as it's empty {}".format(DUPLICATES_DIR))
            rmtree(DUPLICATES_DIR)

if __name__ == "__main__":
    clear()
    logo()
    debug("\n0. Init\n")
    init()
    print("\n1. Index base images\n")
    index_images(BASE_DIR)
    print("\n2. Optimalize images\n")
    optimalize_images(OPTIMALIZED_IMGS_DIR_BASE)
    print("\n3. Find duplicates\n")
    find_duplicate_images(OPTIMALIZED_IMGS_DIR_BASE)
    print("\n4. Index optimalized images\n")
    index_images(OPTIMALIZED_IMGS_DIR_BASE)
    print("\n5. Upscale optimalized images\n")
    upscale_images(OPTIMALIZED_IMGS_DIR_BASE, UPSCALED_IMGS_DIR)
    print("\n6. Index upscaled images\n")
    index_images(UPSCALED_IMGS_DIR)
    print("\n7. Optimalize upscaled images\n")
    optimalize_images(OPTIMALIZED_IMGS_DIR_UPSCALED)
    cleanup()
