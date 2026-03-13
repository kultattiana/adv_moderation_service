import pytest
from repositories.accounts import AccountRepository
from repositories.sellers import SellerRepository
from unittest.mock import AsyncMock, patch
from errors import UnauthorizedError


@pytest.mark.integration
@pytest.mark.asyncio
class TestAccountRepoIntegration:

    async def test_create_and_get_account(self, seller_data, created_account_data: dict):

        account_repo = AccountRepository()
        seller_repo = SellerRepository(account_repo=account_repo)

        seller = {
            **seller_data,
            "is_verified": False
        }

        seller = await seller_repo.create(**seller)

        account = await account_repo.get_by_seller_id(seller.seller_id)

        assert account.id is not None
        assert account.login == seller_data["username"]
        assert account.seller_id == seller.seller_id
        assert account.is_blocked == created_account_data["is_blocked"]

        assert ":" in account.password
        hashed, salt = account.password.split(":", 1)
        assert len(hashed) > 0
        assert len(salt) > 0

        get_account = await account_repo.get_by_id(account.id)

        assert get_account.id == account.id
        assert account.login == get_account.login
        assert account.seller_id == get_account.seller_id
        assert account.is_blocked == get_account.is_blocked


   
    async def test_repository_get_account_by_login_and_password(self, 
                                                                created_account_data, seller_data):
        
        account_repo = AccountRepository()
        seller_repo = SellerRepository(account_repo=account_repo)

        seller = {
            **seller_data,
            "is_verified": False
        }

        seller = await seller_repo.create(**seller)
        account = await account_repo.get_by_seller_id(seller.seller_id)

        with patch('repositories.accounts.verify_password') as mock_verify:

            mock_verify.return_value = True
            retrieved = await account_repo.get_by_login_and_password(
                login=account.login,
                password=account.password
            )
            
            assert retrieved.login == account.login
            assert retrieved.seller_id == account.seller_id
    

    async def test_repository_login_unverified_password(self, created_account_data, seller_data):
        
        account_repo = AccountRepository()
        seller_repo = SellerRepository(account_repo=account_repo)

        seller = {
            **seller_data,
            "is_verified": False
        }

        seller = await seller_repo.create(**seller)
        account = await account_repo.get_by_seller_id(seller.seller_id)

        with patch('repositories.accounts.verify_password') as mock_verify:

            mock_verify.return_value = False

            with pytest.raises(UnauthorizedError):
                retrieved = await account_repo.get_by_login_and_password(
                    login=account.login,
                    password=account.password
                )

    
    async def test_repository_block_account(self, seller_data):

        account_repo = AccountRepository()
        seller_repo = SellerRepository(account_repo=account_repo)

        seller = {
            **seller_data,
            "is_verified": False
        }

        seller = await seller_repo.create(**seller)
        created = await account_repo.get_by_seller_id(seller.seller_id)

        assert created.is_blocked is False
        
        blocked = await account_repo.block(created.id)
        
        assert blocked.id == created.id
        assert blocked.is_blocked is True
        assert blocked.updated_at > created.updated_at


    
    async def test_repository_update_password(self, seller_data):

        account_repo = AccountRepository()
        seller_repo = SellerRepository(account_repo=account_repo)

        seller = {
            **seller_data,
            "is_verified": False
        }

        seller = await seller_repo.create(**seller)
        created = await account_repo.get_by_seller_id(seller.seller_id)

        old_password = created.password
        
        new_password = "new_secure_password456"
        updated = await account_repo.update_password(created.id, new_password)
        
        assert updated.id == created.id
        assert updated.password != old_password
        assert updated.updated_at > created.updated_at
        
        with patch('repositories.accounts.verify_password') as mock_verify:
            mock_verify.return_value = True
            retrieved = await account_repo.get_by_login_and_password(
                login=created.login,
                password=new_password
            )
            assert retrieved.id == created.id


    
    async def test_repository_delete_account(self, seller_data):
        
        account_repo = AccountRepository()
        seller_repo = SellerRepository(account_repo=account_repo)

        seller = {
            **seller_data,
            "is_verified": False
        }

        seller = await seller_repo.create(**seller)
        created = await account_repo.get_by_seller_id(seller.seller_id)
        
        deleted = await account_repo.delete(created.id)
        
        assert deleted.id == created.id
        assert deleted.login == created.login

