import json
import logging
import os
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
rekognition = boto3.client("rekognition")

def lambda_handler(event, context):
    """
    Lambda déclenchée par un upload dans S3.
    Elle détecte les labels avec Rekognition et met à jour le post dans DynamoDB.
    """

    logger.info("Event reçu : %s", json.dumps(event, indent=2))

    table_name = os.getenv("TASKS_TABLE")
    if not table_name:
        raise RuntimeError("La variable d'environnement TASKS_TABLE est manquante")

    table = dynamodb.Table(table_name)

    for record in event.get("Records", []):
        try:
            # Récupération du bucket et de la clé S3
            bucket = record["s3"]["bucket"]["name"]
            key = unquote_plus(record["s3"]["object"]["key"])

            logger.info(f"Bucket : {bucket}")
            logger.info(f"Key : {key}")

            # Format attendu : user/post_id/image_name
            parts = key.split("/")
            if len(parts) < 3:
                logger.warning(f"Format de clé invalide : {key}")
                continue

            user = parts[0]
            post_id = parts[1]

            logger.info(f"User : {user}")
            logger.info(f"Post ID : {post_id}")

            # Appel à Rekognition
            response = rekognition.detect_labels(
                Image={
                    "S3Object": {
                        "Bucket": bucket,
                        "Name": key
                    }
                },
                MaxLabels=5,
                MinConfidence=75.0
            )

            labels = [label["Name"] for label in response.get("Labels", [])]

            logger.info(f"Labels détectés : {labels}")

            # Mise à jour DynamoDB
            table.update_item(
                Key={
                    "user": user,
                    "id": post_id
                },
                UpdateExpression="SET image = :image, label = :label",
                ExpressionAttributeValues={
                    ":image": key,
                    ":label": labels
                }
            )

            logger.info(f"Post mis à jour : user={user}, id={post_id}")

        except Exception as e:
            logger.exception(f"Erreur traitement S3 : {e}")

    return {
        "statusCode": 200,
        "body": "Traitement terminé"
    }