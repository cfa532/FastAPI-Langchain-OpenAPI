# pip install app-store-server-library
import glob, os
from appstoreserverlibrary.api_client import AppStoreServerAPIClient, APIException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.SendTestNotificationResponse import SendTestNotificationResponse
from appstoreserverlibrary.signed_data_verifier import VerificationException, SignedDataVerifier
from typing import List

key_id = "2PMR9NKLU7"
issuer_id = "b806e892-de29-49c9-b54e-8d79584f6c68"
private_key = open('./SubscriptionKey_2PMR9NKLU7.p8', mode="rb").read()
bundle_id = "secretari.leither.uk"               # in app settings
environment = Environment.SANDBOX
app_apple_id = "6499114177" # app Apple ID must be provided for the Production environment
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
    
async def decode_notification(signedPayload):
    try:
        payLoad = signed_data_verifier.verify_and_decode_notification(signedPayload)
        if payLoad.notificationType == "CONSUMPTION_REQUEST":
            print("Refund requested. Send comsumption report")
            transaction = decode_transaction_info(payLoad)
            print("Transaction", transaction)
            return
        elif payLoad.notificationType == "REFUND":
            print("Refund happend. Process it if consumables")
            transaction = decode_transaction_info(payLoad)
            print("Transaction", transaction)
            # transaction_id = transaction.originalTransactionId
            # product_id = transaction.productId

            # https://developer.apple.com/documentation/appstoreservernotifications/notificationtype
            # If it is consumable, process the message. Ignore other types.
            # Search all user records to find that transaction within the user's data. There is a "balance".
            # It is the amount before the recharge of this refund. Restore the balance. Done!
            # To do ....
            return
        else:
            return
        
        if payLoad.data:
            # ResponseBodyV2DecodedPayload
            print("notification type", payLoad.notificationType)
            if payLoad.data.signedTransactionInfo:
                transaction = signed_data_verifier.verify_and_decode_signed_transaction(payLoad.data.signedTransactionInfo)
                print("Transaction", transaction)
                # record the income
            if payLoad.data.signedRenewalInfo:
                renewal = signed_data_verifier.verify_and_decode_renewal_info(payLoad.data.signedRenewalInfo)
                print("Renew", renewal)
        elif payLoad.summary:
            pass
        else:       # externalPurchaseToken
            pass

    except VerificationException as e:
        print("Verifcation except", e)
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