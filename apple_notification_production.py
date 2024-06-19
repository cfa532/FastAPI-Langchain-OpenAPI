# pip install app-store-server-library
import glob, os
from appstoreserverlibrary.api_client import AppStoreServerAPIClient, APIException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.SendTestNotificationResponse import SendTestNotificationResponse
from appstoreserverlibrary.signed_data_verifier import VerificationException, SignedDataVerifier
from typing import List

from utilities import Purchase
environment = Environment.PRODUCTION

# the following three are from Integrations tab of Users and Access in Apple connnect.
key_id = "2PMR9NKLU7"
issuer_id = "b806e892-de29-49c9-b54e-8d79584f6c68"
private_key = open('./SubscriptionKey_2PMR9NKLU7.p8', mode="rb").read()

# The following two are in the App Information page on App Store connect
bundle_id = "secretari.leither.uk"
app_apple_id = "6499114177"                 # app Apple ID must be provided for the Production environment
client = AppStoreServerAPIClient(private_key, key_id, issuer_id, bundle_id, environment)

def load_root_certificates(directory) -> List[bytes]:
    file_contents = []
    # Use glob to find all files with the .cer extension in the specified directory
    cer_files = glob.glob(os.path.join(directory, '*.cer'))
    for file_path in cer_files:
        with open(file_path, 'rb') as file:
            file_contents.append(file.read())
    return file_contents

# load root certificates gloablly
root_certificates = load_root_certificates("./CA")
enable_online_checks = True
signed_data_verifier = SignedDataVerifier(root_certificates, enable_online_checks, environment, bundle_id, app_apple_id)

def decode_transaction_info(payLoad):
    # ResponseBodyV2DecodedPayload
    if payLoad.data and payLoad.data.signedTransactionInfo:
        return signed_data_verifier.verify_and_decode_signed_transaction(payLoad.data.signedTransactionInfo)

def decode_renewal_info(payLoad):
    # ResponseBodyV2DecodedPayload
    if payLoad.data and payLoad.data.signedRenewalInfo:
        return signed_data_verifier.verify_and_decode_signed_transaction(payLoad.data.signedRenewalInfo)
    
async def decode_notification(lapi, signedPayload):
    try:
        payLoad = signed_data_verifier.verify_and_decode_notification(signedPayload)
        print(payLoad.rawNotificationType, payLoad.subtype)

        if payLoad.rawNotificationType == "CONSUMPTION_REQUEST":
            transaction = decode_transaction_info(payLoad)
            print("Refund request:", transaction)

        elif payLoad.rawNotificationType == "ONE_TIME_CHARGE":
            transaction = decode_transaction_info(payLoad)
            print(payLoad.rawNotificationType, transaction)
            p = Purchase(
                notificationType = payLoad.rawNotificationType,
                productId = transaction.productId,
                originalTransactionId = transaction.originalTransactionId,
                originalPurchaseDate = transaction.originalPurchaseDate/1000,
                transactionId = transaction.transactionId,
                purchaseDate = transaction.purchaseDate/1000,       # convert to Python format
                quantity = transaction.quantity)
            # find user who puchased the consumables with appAccountToken from index DB
            lapi.recharge_user(transaction.appAccountToken.upper(), p)

        # for subscribers, just append a new record in purchase history
        elif payLoad.rawNotificationType == "SUBSCRIBED":
            transaction = decode_transaction_info(payLoad)
            print(payLoad.rawNotificationType, payLoad.subtype, transaction)
            p = Purchase(
                notificationType = payLoad.rawNotificationType,
                productId = transaction.productId,
                originalTransactionId = transaction.originalTransactionId,
                originalPurchaseDate = transaction.originalPurchaseDate/1000,
                transactionId = transaction.transactionId,
                purchaseDate = transaction.purchaseDate/1000,       # convert to Python format
                quantity = transaction.quantity)
            lapi.subscribed(transaction.appAccountToken.upper(), p)

        elif payLoad.rawNotificationType == "DID_RENEW":
            transaction = decode_transaction_info(payLoad)
            print(payLoad.rawNotificationType, payLoad.subtype, transaction)
            p = Purchase(
                notificationType = payLoad.rawNotificationType,
                productId = transaction.productId,
                originalTransactionId = transaction.originalTransactionId,
                originalPurchaseDate = transaction.originalPurchaseDate/1000,
                transactionId = transaction.transactionId,
                purchaseDate = transaction.purchaseDate/1000,       # convert to Python format
                quantity = transaction.quantity)
            lapi.subscribed(transaction.appAccountToken.upper(), p)

        elif payLoad.rawNotificationType == "REFUND":
            transaction = decode_transaction_info(payLoad)
            print("Refund happened:", transaction)
            # transaction_id = transaction.originalTransactionId
            # product_id = transaction.productId

            # https://developer.apple.com/documentation/appstoreservernotifications/notificationtype
            # If it is consumable, process the message. Ignore other types.
            # Search all user records to find that transaction within the user's data. There is a "balance".
            # It is the amount before the recharge of this refund. Restore the balance. Done!
            # To do ....
            return
        else:
            print("Unhandled notifications:", payLoad.rawNotificationType)
            transaction = decode_transaction_info(payLoad)
            print(transaction)
            return

    except VerificationException as e:
        print("Decode exception:", e)
        raise e

def request_test_notification():
    client = AppStoreServerAPIClient(private_key, key_id, issuer_id, bundle_id, environment)
    try:    
        response = client.request_test_notification()
        print(response.testNotificationToken)
    except APIException as e:
        print(e)

# load_root_certificates("./CA")
# request_test_notification()