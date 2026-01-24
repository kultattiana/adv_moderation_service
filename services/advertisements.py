
class AdvertisementService:

    async def predict(self, is_verified_seller: bool, images_qty: int):

        if is_verified_seller or images_qty > 0:
            result = True
        else:
            result = False

        return result
