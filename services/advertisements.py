import numpy as np

class AdvertisementService:

    async def predict(self, 
                        model,
                        seller_id: int,
                        is_verified_seller: bool, 
                        item_id: int,
                        name: str,
                        description: str,
                        category: int,
                        images_qty: int):
        
        verified_feature = 1.0 if is_verified_seller else 0.0
        images_normalized = min(images_qty, 10) / 10.0
        desc_length_normalized = len(description) / 1000.0
        category_normalized = category / 100.0
        
        features_array = np.array([[
            verified_feature,
            images_normalized,
            desc_length_normalized,
            category_normalized
        ]])
        
        prediction_class = model.predict(features_array)[0]
        probabilities = model.predict_proba(features_array)[0]
        violation_probability = float(probabilities[1])
        is_violation = bool(prediction_class)

        return is_violation, violation_probability
        
        
