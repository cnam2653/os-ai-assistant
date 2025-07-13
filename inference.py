import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import json
import os

class IntentClassifier:
    def __init__(self, model_path="./intent_model"):
        """Initialize the intent classifier"""
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.label_mapping = None
        self.load_model()
    
    def load_model(self):
        """Load the trained model and tokenizer"""
        try:
            print(f"Loading model from {self.model_path}...")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            
            # Load model
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            self.model.eval()
            
            # Load metadata
            with open(os.path.join(self.model_path, "metadata.json"), "r") as f:
                metadata = json.load(f)
                self.label_mapping = metadata["label_mapping"]
                # Convert string keys to int keys
                self.label_mapping = {int(k): v for k, v in self.label_mapping.items()}
            
            print(f"Model loaded successfully!")
            print(f"Available intents: {list(self.label_mapping.values())}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def predict(self, text, return_probabilities=False):
        """Predict intent for given text"""
        if self.model is None or self.tokenizer is None:
            raise ValueError("Model not loaded. Call load_model() first.")
        
        # Tokenize input
        inputs = self.tokenizer(
            text, 
            return_tensors="pt", 
            padding=True, 
            truncation=True, 
            max_length=32
        )
        
        # Get prediction
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            if return_probabilities:
                # Return all probabilities
                probs_dict = {}
                for i, prob in enumerate(probabilities[0]):
                    intent = self.label_mapping[i]
                    probs_dict[intent] = float(prob)
                return probs_dict
            else:
                # Return top prediction
                predicted_class_id = probabilities.argmax().item()
                confidence = probabilities.max().item()
                predicted_intent = self.label_mapping[predicted_class_id]
                
                return {
                    "intent": predicted_intent,
                    "confidence": float(confidence)
                }
    
    def predict_batch(self, texts):
        """Predict intents for multiple texts"""
        results = []
        for text in texts:
            result = self.predict(text)
            results.append({"text": text, **result})
        return results

def main():
    """Main function to test the classifier"""
    print("Intent Classification Demo")
    print("=" * 40)
    
    # Initialize classifier
    try:
        classifier = IntentClassifier()
    except Exception as e:
        print(f"Failed to load model: {e}")
        print("Make sure you have trained the model first by running:")
        print("1. python data_augmentation.py")
        print("2. python train_transformer_intent.py")
        return
    
    # Test cases
    test_cases = [
        "open chrome browser",
        "close notepad",
        "what's the weather in New York",
        "search for python programming",
        "type my password",
        "press enter key",
        "take a screenshot",
        "read what's on screen",
        "increase volume",
        "what time is it now",
        "what's today's date",
        "send email to john",
        "open my document",
        "launch spotify",
        "quit discord",
        "weather in London",
        "google machine learning",
        "mute the sound",
        "current time please"
    ]
    
    print("\nTesting with sample inputs:")
    print("-" * 60)
    
    for text in test_cases:
        result = classifier.predict(text)
        print(f"'{text}' → {result['intent']} (confidence: {result['confidence']:.3f})")
    
    # Interactive mode
    print("\n" + "=" * 60)
    print("Interactive Mode (type 'quit' to exit)")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\nEnter command: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Get prediction
            result = classifier.predict(user_input)
            
            # Also get top 3 predictions
            probs = classifier.predict(user_input, return_probabilities=True)
            top_3 = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
            
            print(f"\nTop prediction: {result['intent']} (confidence: {result['confidence']:.3f})")
            print("Top 3 predictions:")
            for i, (intent, prob) in enumerate(top_3, 1):
                print(f"  {i}. {intent}: {prob:.3f}")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()