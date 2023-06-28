from typing import Annotated
from fastapi import Depends, FastAPI, Form, HTTPException, Path, APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from models import Users
from database import SessionLocal, engine
from starlette import status
from .auth import get_curr_user
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import models
from starlette.responses import RedirectResponse
import folium
from folium.features import DivIcon
import pandas as pd
import warnings
warnings.filterwarnings("ignore")


router = APIRouter(
    prefix = '/map',
    tags = ['map']
)

models.Base.metadata.create_all(bind=engine)

templates =  Jinja2Templates(directory="templates")

#opens and closes a connection to the Sessions database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

data = pd.read_csv('static/ICARUS Galapagos tortoises.csv')
data = data[['event-id','timestamp','location-long','location-lat','tag-local-identifier']]
data = data.dropna()
data['tag-local-identifier'] = data['tag-local-identifier'].astype(str)
data['timestamp'] = data['timestamp'].astype(str)
unique_turtles = data['tag-local-identifier'].unique().tolist()
#['A1661B', '87894E', '94C7A1', '93CE2D', 'A2AD71']

def get_coordinates(tag):
    temp = data[data['tag-local-identifier'] == tag]
    temp.sort_values(by='timestamp')
    temp['location-long'] = temp['location-long'] -44.4
    temp['timestamp'] = temp['timestamp'].apply(lambda x: x.split()[-1])
    coordinates = temp[['location-long', 'location-lat','timestamp']].values.tolist()
    return coordinates


def plot_points_on_map(tag, day):
    points = get_coordinates(tag)
    points = points[:day]
    if len(points) > 0:
        map_center = [sum(p[1] for p in points) / len(points), sum(p[0] for p in points) / len(points)]
    else:
        map_center = [0, 0]
    world_map = folium.Map(location=map_center, zoom_start=14, crs='EPSG4326')

    for i, point in enumerate(points):
        coordinates = (point[1], point[0])
        timestamp = point[2]
        div_icon = DivIcon(icon_size=(150,36), icon_anchor=(75,18), html=f'<div style="font-weight: bold;">{timestamp}</div>')
        folium.Marker(location=(point[1], point[0])).add_to(world_map)
        folium.Marker(location=coordinates, icon=div_icon).add_to(world_map)
        if i > 0:
            prev_coordinates = (points[i-1][1], points[i-1][0])
            folium.PolyLine([prev_coordinates, coordinates], color='blue', weight=2.5).add_to(world_map)
        

    return world_map


def map(tag,day):
    map_with_points = plot_points_on_map(tag, day)
    map_with_points.save('templates/map.html')

@router.get("/", response_class=HTMLResponse)
async def read_map(request:Request, db: Session=Depends(get_db)):
    user = await get_curr_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    model = db.query(Users).filter(Users.id==user.get('id')).first()
    map(model.tag,model.day)
    model.day += 1
    if model.day >= 30:
        model.day = 1
    firstname = model.firstname
    lastname = model.lastname
    db.add(model)
    db.commit()
    return templates.TemplateResponse("display.html",{"request":request, "firstname":firstname, "lastname":lastname})


@router.post("/", response_class=HTMLResponse)
async def update_todo(request:Request, first: str=Form(...), last:str=Form(...), db: Session=Depends(get_db)):
    user = await get_curr_user(request)
    if user is None:
        return RedirectResponse(url="/auth", status_code=status.HTTP_302_FOUND)
    model = db.query(Users).filter(Users.id==user.get('id')).first()
    model.firstname = first
    model.lastname = last
    db.add(model)
    db.commit()
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)