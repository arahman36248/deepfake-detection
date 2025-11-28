"""
Download and setup deepfake dataset for training
Alternative to bash script - works more reliably
"""
import os
import sys
import subprocess
import zipfile
from pathlib import Path
import urllib.request
from tqdm import tqdm

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def download_file(url, output_path):
    """Download file with progress bar"""
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=output_path.name) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)

def setup_dataset():
    print("="*70)
    print("DEEPFAKE DATASET SETUP")
    print("="*70)
    print()
    
    # Check if we're in the right directory
    if not Path('app.py').exists():
        print("ERROR: Please run this script from the deepfake-detection directory")
        sys.exit(1)
    
    # Create directories
    print("1. Creating dataset directories...")
    base_dir = Path('datasets/deepfake')
    real_dir = base_dir / 'real'
    fake_dir = base_dir / 'fake'
    temp_dir = Path('datasets/temp')
    
    real_dir.mkdir(parents=True, exist_ok=True)
    fake_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Install gdown if not present
    print("\n2. Installing gdown...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'gdown', '--quiet'])
    
    # Import gdown after installation
    import gdown
    
    # Download datasets
    print("\n3. Downloading datasets...")
    print("   This will download ~2GB of data (may take 10-20 minutes)")
    print()
    
    # Option 1: Kaggle 140k dataset (smaller, faster)
    print("   Using: 140k Real and Fake Faces dataset")
    print()
    
    # Download real faces
    print("   Downloading REAL faces (700MB)...")
    real_zip = temp_dir / 'real_faces.zip'
    
    # Try multiple sources
    real_url = "https://www.dropbox.com/s/wrtumxjbu3e256y/real_and_fake_face.zip?dl=1"
    
    try:
        download_file(real_url, real_zip)
    except Exception as e:
        print(f"   Download failed: {e}")
        print("   Trying alternative method with gdown...")
        
        # Alternative: Use Kaggle API or direct links
        print("   Please download manually from:")
        print("   https://www.kaggle.com/datasets/ciplab/real-and-fake-face-detection")
        print("   Extract to: datasets/deepfake/")
        return
    
    # Extract
    print("\n4. Extracting datasets...")
    print("   This may take 5-10 minutes...")
    
    with zipfile.ZipFile(real_zip, 'r') as zip_ref:
        # Extract to temporary location first
        zip_ref.extractall(temp_dir)
    
    # Move files to correct locations
    print("\n5. Organizing files...")
    
    # Find extracted folders
    extracted_dir = temp_dir / 'real_and_fake_face'
    
    if extracted_dir.exists():
        # Move real images
        real_source = extracted_dir / 'training_real'
        if real_source.exists():
            for img in real_source.glob('*.jpg'):
                img.rename(real_dir / img.name)
            for img in real_source.glob('*.png'):
                img.rename(real_dir / img.name)
        
        # Move fake images  
        fake_source = extracted_dir / 'training_fake'
        if fake_source.exists():
            for img in fake_source.glob('*.jpg'):
                img.rename(fake_dir / img.name)
            for img in fake_source.glob('*.png'):
                img.rename(fake_dir / img.name)
    
    # Clean up
    print("\n6. Cleaning up...")
    import shutil
    shutil.rmtree(temp_dir)
    
    # Count images
    real_count = len(list(real_dir.glob('*.jpg')) + list(real_dir.glob('*.png')))
    fake_count = len(list(fake_dir.glob('*.jpg')) + list(fake_dir.glob('*.png')))
    
    print()
    print("="*70)
    print("DATASET SETUP COMPLETE")
    print("="*70)
    print(f"Real images: {real_count}")
    print(f"Fake images: {fake_count}")
    print(f"Total images: {real_count + fake_count}")
    print()
    
    if real_count > 0 and fake_count > 0:
        # Ask about training
        response = input("Start training now? (y/n): ")
        if response.lower() == 'y':
            print("\nStarting training...")
            os.system('python3 train_model.py --dataset datasets/deepfake --epochs 15 --batch-size 8')
        else:
            print("\nTo train later, run:")
            print("  python3 train_model.py --dataset datasets/deepfake --epochs 15")
    else:
        print("WARNING: No images found!")
        print("Please download manually from:")
        print("https://www.kaggle.com/datasets/ciplab/real-and-fake-face-detection")

if __name__ == '__main__':
    try:
        setup_dataset()
    except KeyboardInterrupt:
        print("\n\nDownload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nIf automatic download fails, please download manually:")
        print("1. Visit: https://www.kaggle.com/datasets/ciplab/real-and-fake-face-detection")
        print("2. Download the dataset")
        print("3. Extract to datasets/deepfake/ with subfolders real/ and fake/")
        sys.exit(1)
