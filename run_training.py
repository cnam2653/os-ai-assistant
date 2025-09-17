#!/usr/bin/env python3
"""
Training Runner Script
This script helps you run the training process step by step
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"STEP: {description}")
    print(f"{'='*60}")
    print(f"Running: {command}")
    print("-" * 60)
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=False)
        print(f"\n{description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n{description} failed with error code: {e.returncode}")
        return False

def main():
    """Main function to run the training pipeline"""
    print("Intent Classification Training Pipeline")
    print("=" * 60)

    # Check if we're in the right directory
    if not os.path.exists("data"):
        print("Error: 'data' directory not found.")
        print("Please run this script from the project root directory where 'data' folder exists.")
        sys.exit(1)

    if not os.path.exists("models"):
        print("Error: 'models' directory not found.")
        print("Please make sure you have the 'models' folder with your training scripts.")
        sys.exit(1)

    # Check if original data exists
    if not os.path.exists("data/intents.csv"):
        print("Error: 'data/intents.csv' not found.")
        print("Please make sure your original dataset exists.")
        sys.exit(1)

    print("Directory structure looks good!")
    print(f"Current directory: {os.getcwd()}")
    print(f"Found data folder: {os.path.exists('data')}")
    print(f"Found models folder: {os.path.exists('models')}")
    print(f"Found intents.csv: {os.path.exists('data/intents.csv')}")

    # Step 1: Data Augmentation
    success = run_command(
        "cd models && python data_augmentation.py",
        "Data Augmentation"
    )
    if not success:
        print("\nData augmentation failed. Please check the errors above.")
        sys.exit(1)

    # Check if augmented data was created
    if not os.path.exists("data/intents_augmented.csv"):
        print("Error: Augmented dataset was not created!")
        sys.exit(1)

    # Step 2: Model Training
    success = run_command(
        "cd models && python train_transformer_intent.py",
        "Model Training"
    )
    if not success:
        print("\nModel training failed. Please check the errors above.")
        sys.exit(1)

    # Check if model was created
    if not os.path.exists("intent_model"):
        print("Error: Model was not saved!")
        sys.exit(1)

    # Step 3: Test the model (optional)
    print(f"\n{'='*60}")
    print("TRAINING COMPLETE")
    print(f"{'='*60}")
    print("\nFiles created:")
    print(f" data/intents_augmented.csv - Augmented dataset")
    print(f" intent_model/ - Trained model files")
    print(f" results/ - Training logs and checkpoints")

    # Offer to run inference
    try:
        response = input("\nWould you like to test the model now? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            print("\nRunning inference test...")
            run_command(
                "python inference.py",
                "Model Testing"
            )
    except KeyboardInterrupt:
        print("\nSkipping inference test.")

    print(f"\n{'='*60}")
    print("All done! Your intent classification model is ready to use.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
