#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
import boto3
from botocore.config import Config
import os
import uuid
from dotenv import load_dotenv
from typing import Union
import logging
from fastapi import FastAPI, Request, status, Header
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from getSignedUrl import getSignedUrl

load_dotenv()

app = FastAPI()
logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
    logger.error(f"{request}: {exc_str}")
    content = {'status_code': 10422, 'message': exc_str, 'data': None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class Post(BaseModel):
    title: str
    body: str

my_config = Config(
    region_name='us-east-1',
    signature_version='v4',
)

dynamodb = boto3.resource('dynamodb', config=my_config)
table = dynamodb.Table(os.getenv("DYNAMO_TABLE"))
s3_client = boto3.client('s3', config=boto3.session.Config(signature_version='s3v4'))
bucket = os.getenv("BUCKET")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################


@app.post("/posts")
async def post_a_post(post: Post, authorization: str | None = Header(default=None)):
    """
    Poste un post ! Les informations du poste sont dans post.title, post.body et le user dans authorization
    """
    logger.info(f"title : {post.title}")
    logger.info(f"body : {post.body}")
    logger.info(f"user : {authorization}")

    post_id = f"POST#{uuid.uuid4()}"

    res = table.put_item(
        Item={
            "user": authorization,
            "id": post_id,
            "title": post.title,
            "body": post.body,
            "label": [],
        }
    )

    return res


@app.get("/posts")
async def get_all_posts(user: Union[str, None] = None):
    """
    Recupere tout les postes.
    - Si un user est present dans la requete, recupere uniquement les siens
    - Si aucun user n'est present, recupere TOUS les postes de la table
    """
    if user:
        logger.info(f"Recuperation des postes de : {user}")
        res = get_posts_by_user(user)
    else:
        logger.info("Recuperation de tous les postes")
        res = get_all_posts_from_db()

    return res


def get_all_posts_from_db():
    """Scan complet de la table DynamoDB."""
    res = table.scan()
    items = res.get("Items", [])
    return [format_post(item) for item in items]


def get_posts_by_user(username: str):
    """Query sur la partition key user."""
    from boto3.dynamodb.conditions import Key
    res = table.query(
        KeyConditionExpression=Key("user").eq(username)
    )
    items = res.get("Items", [])
    return [format_post(item) for item in items]


def format_post(item: dict) -> dict:
    """Formate un item DynamoDB et genere l'URL presignee pour l'image."""
    image_url = None
    if item.get("image"):
        try:
            image_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": item["image"]},
                ExpiresIn=3600,
            )
        except Exception as e:
            logger.error(f"Erreur generation URL presignee : {e}")

    return {
        "user": item.get("user"),
        "id": item.get("id"),
        "title": item.get("title"),
        "body": item.get("body"),
        "image": image_url,
        "label": item.get("label", []),
    }


@app.delete("/posts/{post_id}")
async def delete_post(post_id: str, authorization: str | None = Header(default=None)):
    logger.info(f"post id : {post_id}")
    logger.info(f"user: {authorization}")

    # Recuperation des infos du poste
    res = table.get_item(
        Key={"user": authorization, "id": post_id}
    )
    item = res.get("Item")

    # S'il y a une image on la supprime de S3
    if item and item.get("image"):
        try:
            s3_client.delete_object(Bucket=bucket, Key=item["image"])
            logger.info(f"Image supprimee de S3 : {item['image']}")
        except Exception as e:
            logger.error(f"Erreur suppression S3 : {e}")

    # Suppression de la ligne dans la base dynamodb
    result = table.delete_item(
        Key={"user": authorization, "id": post_id}
    )

    return result


#################################################################################################
##                                                                                             ##
##                                 NE PAS TOUCHER CETTE PARTIE                                 ##
##                                                                                             ##
## 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 👇 ##
@app.get("/signedUrlPut")
async def get_signed_url_put(filename: str, filetype: str, postId: str, authorization: str | None = Header(default=None)):
    return getSignedUrl(filename, filetype, postId, authorization)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")

## ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ☝️ ##
##                                                                                                ##
####################################################################################################
